function schedule = read_snap_schedule(csvPath)
%READ_SNAP_SCHEDULE Read a SNAP benchmark schedule CSV file.
%
% Example:
%   schedule = read_snap_schedule("../instances/snap_s_001/planted_solution.csv");

    schedule = readtable(csvPath, 'TextType', 'string');
end
