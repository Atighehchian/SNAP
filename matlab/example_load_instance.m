% Example: load SNAP instance and planted schedule in MATLAB

instance = read_snap_instance("../instances/snap_s_001/instance.json");
schedule = read_snap_schedule("../instances/snap_s_001/planted_solution.csv");

disp(instance.metadata.instance_id);
disp(head(schedule));
