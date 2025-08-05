function VISAAddresses = listACEVISAAddresses
%LISTACEVISAADDRESSES returns the VISA resource strings of all instruments configured in Agilent Connection Expert
%   This function returns a cell array of strings, with each cell
%   containing a VISA address of an instrument that has been configured in
%   Agilent Connection Expert. The function assumes that Agilent IO Suite
%   has been installed

% Copyright 2012 MathWorks

VISAAddresses = {};
AgilentVISAInfo = instrhwinfo('visa','agilent');
for iLoop = 1:length(AgilentVISAInfo.ObjectConstructorName)
    VISAAddresses{end+1} = AgilentVISAInfo.ObjectConstructorName{iLoop}(18:(end-3)); %#ok
end
end

