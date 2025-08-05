function [IQdata,sampleRate] = deepCapture(VISAAddress, span, sRate, requestedTime, blockSize, timeout, centerFreq)
%% This function connects to an X-Series analyzer via VISA to acquire
% up to 536,870,908 IQ sample pairs from the VXA Measurement Option.
% 2GB capture memory is required.  Option DP2 is the 2 GB memory, although
% instruments with B1X, B1Y, B40, or MPB also implicitly have 2 GB memory
% X-Series software A.11.02 and later is required, since this is when
% fast capture / deep capture functionality was added to the I/Q Analyzer
% mode.
% For the example capture bandwidth of 40 MHz, capture length
% of 0.1 seconds, and block transfer size of 100,000, it will take
% approximately 11 seconds to grab 5 million I/Q samples from
% an X Series analyzer via USB or LAN.
%
%% Initial instrument settings
% Create the VISA Object to which to connect to
visaObj = instrfind('Tag','deepCapture');
if isempty(visaObj)
    visaObj = visa('agilent',VISAAddress, 'Tag', 'deepCapture');
else
    fclose(visaObj);
end
% Set the Buffer size - this will depend on your blockSize parameter
% 8 bytes/point * 2 (1 each for I & Q) + additional block for buffer
visaObj.InputBufferSize = (blockSize+1)*8*2;
% Set the Endianness of the data
visaObj.ByteOrder = 'bigEndian';
% Set the EOS Mode
visaObj.EOSMode = 'read&write';
% Set the EOS Character
visaObj.EOSCharCode = 'LF';
% Open the VISA interface connection
fopen(visaObj);
% Temporarily set the timeout value to 45 seconds to allow for
% the initial mode switch to the VXA application
% Note: if also setting the alignments to "partial" it is necessary
% to set the timeout value to 120 seconds to allow the alignment to
% run and the instrument to change modes.
visaObj.Timeout = timeout;
% Reset the analyzer, Clear Error Queue & Status Registers
% set internal alignments to Partial
fprintf(visaObj,'*RST;*CLS');

% Check to make sure we are connected to a N90x0A
idn = query(visaObj,'*IDN?');
mdlIndx = regexpi(idn, 'N90[0-3]+0A');
if isempty(mdlIndx)
    myException = MException('DeepCapture:Incorrectinstrument','Confirm that you have an X-Series analyzer at the specified VISA address');
    throw(myException);
end

%Check to make sure we can do deep capture
%Most instruments with 2GB capture memory will have option DP2; however
%there are some early PXAs that don't have a license key for DP2 but do
%have a license key for either B40,B1X, or B1Y.  Similarly, there are some
%MXAs with option MPB that don't have DP2.
opt = query(visaObj,'*OPT?'); 
dp2Indx = regexpi(opt,'DP2');
b40Indx = regexpi(opt,'B40');
b1xIndx = regexpi(opt,'B1X');
b1yIndx = regexpi(opt,'B1Y');
mpbIndx = regexpi(opt,'MPB');

if (isempty(dp2Indx) && isempty (b40Indx) && isempty (b1xIndx) && isempty (b1yIndx) && isempty (mpbIndx))
    myException = MException('DeepCapture:Optionunavailable','It appears that your instrument does not have 2GB capture memory');
    throw(myException);   
end

% Set instrument to IQ Basic mode
fprintf(visaObj,':INST:SEL BASIC');

% Clear error queue and do a mode preset
fprintf(visaObj,'*CLS;*RST');

% configure waveform
fprintf(visaObj,':CONF:WAV');

% Set desired center Frequency
fprintf(visaObj,[':FREQ:CENT ' num2str(centerFreq)]);
fprintf(visaObj, [':WAV:SRAT ' num2str(sRate) ' MHz']);

sampleRate = str2double(query(visaObj, ':WAV:SRATe?'));

% Set SCPI Read Format  (Possible settings are REAL, 32;  REAL, 64)
fprintf(visaObj,':FORM REAL,32');

% Initiate a fast capture (deep capture)
fprintf(visaObj, ':INIT:FCAP');

% Query to determine when meausurement is complete
opVal = query(visaObj, '*OPC?');

% Query max capture length in points and put into variable "maxLength"
maxLength = str2double(query(visaObj,':FCAP:LENG? MAX'));

% Set the timeout value back to user provided timeout for reading the data
visaObj.Timeout = timeout;

% Adjust maximum based on instrument capabilities
maxTime = maxLength / sampleRate;
if (requestedTime > maxTime)
    requestedTime = maxTime;
end

% Calculate the number of points to request from the instrument
reqPoint = int32(requestedTime * sampleRate);
if ~isequal(mod(reqPoint,2),0)
    reqPoint = reqPoint-1;
end

% Set capture length in points  Use an even number when bit packing is AUTO or BIT32
fprintf(visaObj,[':FCAP:LENG ' num2str(reqPoint)]);

% Initiate fast capture
fprintf(visaObj,':INIT:FCAP');

loopTillComplete(visaObj);

% Query Max read block size and put into variable "maxBlock"
maxBlock = str2double(query(visaObj,':FCAP:BLOC? MAX'));

% Reduce Block size to maximum block size if it is too big
if (blockSize > maxBlock)
    blockSize = maxBlock;
end

% Block size should be an integer
blockSize = int32(blockSize);

% Block size must be divisible by 2.  Subtract 1 if it is not. Block size does not need to divide evenly into buffer length.
if ~isequal(mod(blockSize,2),0)
    blockSize = blockSize - 1;
end

% Set blockSize for Fast Capture
fprintf(visaObj,[':FCAP:BLOC ' num2str(blockSize)]);

%%  Read out capture data (read pointer auto-increments by the read block size) 
% preallocate the data to read back
IQdata = zeros(1,ceil(reqPoint));
readPointer = int32(0);
tic
while ((reqPoint - readPointer)>1)
    % Binblock read in float64 precision
    fprintf(visaObj,'FETCH:FCAP?');
    rawData = binblockread(visaObj,'float32');
    fread(visaObj, 1);
    
    resIQ = reshape(rawData.', 2, length(rawData)/2).';
    
    if ~(isempty(resIQ))
        IQdata(readPointer+1:readPointer+length(resIQ)) = complex(resIQ(:,1), resIQ(:,2));
    end
    
    loopTillComplete(visaObj);
    
    % Cycle through and display any instrument errors
    stopCondition = 1;
    while isequal(stopCondition,1)
        % Read any errors.
        instrumentError = query(visaObj,'SYST:ERR?');
        % ******** UNCOMMENT THE FOLLOWING LINE TO DISPLAY ERRORS ********
%         disp(instrumentError);
        
        % if error does not have "No error", read all of the errors and display them
        % Note that the last read may return error '-200,"Execution error;Requested data block only partially filled, not enough data."'
        % because the amount of data left in the buffer is not a full read block length. The data returned is still valid.
        stopCondition = isempty(strfind(instrumentError,'No error'));
    end
    
    % You can query the current read pointer position Random access to the capture data is also possible by
    % explicitly setting the read pointer. (Set pointer position to an even number when bit packing is AUTO or BIT32.)
    readPointer = int32(str2double(query(visaObj,':FCAP:POIN?')));
end
toc

% Close the VISA interface connection
fclose(visaObj);
% Delete the object and clear it from memory
delete(visaObj); clear visaObj

%% subfunction to loop till an Operation Complete is returned by the instrument
    function loopTillComplete(visaObj)
        pState = pause('query'); pause('on');
        while ~isequal(str2double(query(visaObj,'*OPC?')),1)
            pause(1);
        end
        pause(pState);
    end
end