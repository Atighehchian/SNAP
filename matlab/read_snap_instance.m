function instance = read_snap_instance(jsonPath)
%READ_SNAP_INSTANCE Read a SNAP benchmark instance JSON file.
%
% Example:
%   instance = read_snap_instance("../instances/snap_s_001/instance.json");

    txt = fileread(jsonPath);
    instance = jsondecode(txt);
end
