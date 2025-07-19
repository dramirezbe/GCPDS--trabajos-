function varargout = DeepCaptureGUI(varargin)
% DEEPCAPTUREGUI M-file for DeepCaptureGUI.fig
%      DEEPCAPTUREGUI, by itself, creates a new DEEPCAPTUREGUI or raises the existing
%      singleton*.
%
%      H = DEEPCAPTUREGUI returns the handle to a new DEEPCAPTUREGUI or the handle to
%      the existing singleton*.
%
%      DEEPCAPTUREGUI('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in DEEPCAPTUREGUI.M with the given input arguments.
%
%      DEEPCAPTUREGUI('Property','Value',...) creates a new DEEPCAPTUREGUI or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before DeepCaptureGUI_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to DeepCaptureGUI_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help DeepCaptureGUI

% Last Modified by GUIDE v2.5 30-Oct-2012 11:55:34

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @DeepCaptureGUI_OpeningFcn, ...
                   'gui_OutputFcn',  @DeepCaptureGUI_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before DeepCaptureGUI is made visible.
function DeepCaptureGUI_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to DeepCaptureGUI (see VARARGIN)

handles.output = hObject;

% Create the MATLAB logo on the GUI
paxis = handles.membraneplot;
generateMATLABLogo(paxis);

% Populate the xlabel, ylabel
xlabel(handles.axes_spectrum_plot, 'Frequency');
ylabel(handles.axes_spectrum_plot, 'Power (dB)');
handles.plothandle = plot(handles.axes_spectrum_plot, 0);
set(handles.axes_spectrum_plot, 'Color', [0 0 0]);
grid(handles.axes_spectrum_plot, 'on');
set(handles.axes_spectrum_plot, 'xcolor', 'w');
set(handles.axes_spectrum_plot, 'ycolor', 'w');

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes DeepCaptureGUI wait for user response (see UIRESUME)
% uiwait(handles.figure1);

% --- Outputs from this function are returned to the command line.
function varargout = DeepCaptureGUI_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;

function txtVISAAddress_Callback(hObject, eventdata, handles)
% hObject    handle to txtVISAAddress (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtVISAAddress as text
%        str2double(get(hObject,'String')) returns contents of txtVISAAddress as a double


% --- Executes during object creation, after setting all properties.
function txtVISAAddress_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtVISAAddress (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function txtSpan_Callback(hObject, eventdata, handles)
% hObject    handle to txtSpan (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtSpan as text
%        str2double(get(hObject,'String')) returns contents of txtSpan as a double


% --- Executes during object creation, after setting all properties.
function txtSpan_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtSpan (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function txtsRate_Callback(hObject, eventdata, handles)
% hObject    handle to txtsRate (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtsRate as text
%        str2double(get(hObject,'String')) returns contents of txtsRate as a double

function txtBlockSize_Callback(hObject, eventdata, handles)
% hObject    handle to txtsRate (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtsRate as text
%        str2double(get(hObject,'String')) returns contents of txtsRate as a double

% --- Executes during object creation, after setting all properties.
function txtsRate_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtsRate (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function txtTime_Callback(hObject, eventdata, handles)
% hObject    handle to txtTime (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtTime as text
%        str2double(get(hObject,'String')) returns contents of txtTime as a double


% --- Executes during object creation, after setting all properties.
function txtTime_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtTime (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes during object creation, after setting all properties.
function txtBlockSize_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtBlockSize (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes when selected object is changed in optPostAcq.
function optPostAcq_SelectionChangeFcn(hObject, eventdata, handles)
% hObject    handle to the selected object in optPostAcq 
% eventdata  structure with the following fields (see UIBUTTONGROUP)
%	EventName: string 'SelectionChanged' (read only)
%	OldValue: handle of the previously selected object or empty if none was selected
%	NewValue: handle of the currently selected object
% handles    structure with handles and user data (see GUIDATA)
switch get(eventdata.NewValue,'Tag') % Get Tag of selected object.
    case 'optVisualize'
        % User changed selection to 'Visualize'
        set(handles.optPostAcq,'UserData',1);
    case 'optSave'
        % User changed selection to 'Save'
        set(handles.optPostAcq,'UserData',2);
    otherwise
        % Code for when there is no match.
end
guidata(hObject, handles)


% --- Executes on button press in btnGetData.
function btnGetData_Callback(hObject, eventdata, handles)
% hObject    handle to btnGetData (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Update Status
set(handles.txtStatus,'String','   Status: Trying to acquire data ...'); drawnow;

% Get VISA address from GUI
VISAAddresses = get(handles.visa_popup,'String');
VISAValue     = get(handles.visa_popup, 'Value');
VISAAddress   = VISAAddresses{VISAValue}; 

% Get Acquisition data

span = str2double(get(handles.txtSpan,'String'));
sRate = 1.25*span/1e6;
requestedTime = str2double(get(handles.txtTime,'String'));
blockSize = str2double(get(handles.txtBlockSize,'String'));
timeout = str2double(get(handles.txtTimeout,'String'));
centerFreq = str2double(get(handles.txtFreq,'String'));

% Basic error check of input parameters
if ~isnan(blockSize) && ~isnan(requestedTime) && ~isnan(sRate) && ~isnan(span) && ~isnan(timeout)
    try
        % Get IQ data
        [IQData, sampleRate] = deepCapture(VISAAddress, span, sRate, requestedTime, blockSize, timeout, centerFreq);
        
        % Calculate periodogram of the acquired IQ data
        % Uncomment the below line to improve resolution of frequency
        % domain plot, and the comment the line after
%         nfft = 2^(nextpow2(length(IQData)));
        nfft = length(IQData);
        [pxx, f]     = periodogram(IQData, [], nfft, sampleRate);
        
        % Update the GUI plot with the periodogram plot
        plot(handles.axes_spectrum_plot, f-max(f)/2, 10*log10(fftshift(pxx)), 'y')
        
        % Set the properties of the GUI Axes
        set(handles.axes_spectrum_plot, 'Color', [0 0 0]);
        grid(handles.axes_spectrum_plot, 'on');
        set(handles.axes_spectrum_plot, 'xcolor', 'w');
        set(handles.axes_spectrum_plot, 'ycolor', 'w');
        axis(handles.axes_spectrum_plot, 'tight');
        xlabel(handles.axes_spectrum_plot, 'Frequency (Hz)');
        ylabel(handles.axes_spectrum_plot, 'Power (dB)');
    catch myException
        % Unable to capture data
        msgbox(['Unable to retrieve IQ Data:' myException.message],'DeepCaptureGUI');
        set(handles.txtStatus,'String','   Status: Waiting for user input');
        return;
    end
    
    switch get(handles.optPostAcq,'UserData')
        case 1
            % Plot IQ Data            
            plot(handles.Iplot, real(IQData), 'g'); xlabel(handles.Iplot, 'Sample number'); ylabel(handles.Iplot, 'Inphase value');            
            title('Plot of Inphase and Quadrature values');
            plot(handles.Qplot, imag(IQData), 'g'); xlabel(handles.Qplot, 'Sample number'); ylabel(handles.Qplot, 'Quadrature value');
            
            % Set the properties of the axis
            set(handles.Iplot, 'Color', [0 0 0]);
            grid(handles.Iplot, 'on');
            set(handles.Iplot, 'xcolor', 'w');
            set(handles.Iplot, 'ycolor', 'w');
            
            set(handles.Qplot, 'Color', [0 0 0]);
            grid(handles.Qplot, 'on');
            set(handles.Qplot, 'xcolor', 'w');
            set(handles.Qplot, 'ycolor', 'w');
            
            axis(handles.axes_spectrum_plot, 'tight');
            xlabel(handles.axes_spectrum_plot, 'Frequency (Hz)');
            ylabel(handles.axes_spectrum_plot, 'Power (dB)');
            
        case 2
            % Get user input for filename and path
            [file,path] = uiputfile('*.mat','Save IQ Data As');
            if ~isequal(file,0) && ~isequal(path,0)
                try
                    % try to save file
                    save(fullfile(path, file), 'IQData');
                catch myException
                    % Error occurred trying to save the file
                    msgbox(['Unable to save IQ Data:' myException.message]);
                    set(handles.txtStatus,'String','   Status: Waiting for user input'); drawnow;
                    return;
                end
            end
        otherwise
            % We should never be here
            msgbox('Please select post acquisition action','DeepCaptureGUI');
    end
else
    % Invalid inputs in one of the input parameters
    msgbox('Invalid Inputs','DeepCaptureGUI');
end
set(handles.txtStatus,'String','   Status: Waiting for user input'); drawnow;



function txtTimeout_Callback(hObject, eventdata, handles)
% hObject    handle to txtTimeout (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtTimeout as text
%        str2double(get(hObject,'String')) returns contents of txtTimeout as a double


% --- Executes during object creation, after setting all properties.
function txtTimeout_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtTimeout (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function txtFreq_Callback(hObject, eventdata, handles)
% hObject    handle to txtFreq (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtFreq as text
%        str2double(get(hObject,'String')) returns contents of txtFreq as a double


% --- Executes during object creation, after setting all properties.
function txtFreq_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtFreq (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function txtMaxCaptureTime_Callback(hObject, eventdata, handles)
% hObject    handle to txtMaxCaptureTime (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of txtMaxCaptureTime as text
%        str2double(get(hObject,'String')) returns contents of txtMaxCaptureTime as a double


% --- Executes during object creation, after setting all properties.
function txtMaxCaptureTime_CreateFcn(hObject, eventdata, handles)
% hObject    handle to txtMaxCaptureTime (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on key press with focus on txtSpan and none of its controls.
function txtSpan_KeyPressFcn(hObject, eventdata, handles)
% hObject    handle to txtSpan (see GCBO)
% eventdata  structure with the following fields (see UICONTROL)
%	Key: name of the key that was pressed, in lower case
%	Character: character interpretation of the key(s) that was pressed
%	Modifier: name(s) of the modifier key(s) (i.e., control, shift) pressed
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in btnUpdateMaxCapTime.
function btnUpdateMaxCapTime_Callback(hObject, eventdata, handles)
% hObject    handle to btnUpdateMaxCapTime (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
newValue = 536870908/(1.25*str2num(get(handles.txtSpan,'String')));
set(handles.txtMaxCaptureTime,'String',newValue);
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on selection change in visa_popup.
function visa_popup_Callback(hObject, eventdata, handles)
% hObject    handle to visa_popup (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns visa_popup contents as cell array
%        contents{get(hObject,'Value')} returns selected item from visa_popup


% --- Executes during object creation, after setting all properties.
function visa_popup_CreateFcn(hObject, eventdata, handles)
% hObject    handle to visa_popup (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end
vAddress = listACEVISAAddresses();
set(hObject, 'String', vAddress);


% --- Executes on button press in viewMLScript.
% function viewMLScript_Callback(hObject, eventdata, handles)
function viewMLScript_Callback(hObject, eventdata, handles)
% hObject    handle to viewMLScript (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
edit('deepCapture.m');
