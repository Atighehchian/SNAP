from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Sequence


def matlab_safe_function_name(instance_id: str) -> str:
    """Return a valid, unique MATLAB function name for an instance loader."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", instance_id.strip())
    if not cleaned or not cleaned[0].isalpha():
        cleaned = "snap_" + cleaned
    return f"load_{cleaned}"


def write_instance_matlab_loader(
    path: str | Path,
    instance: Dict[str, Any],
    schedule: Sequence[Dict[str, Any]],
    metadata: Dict[str, Any],
) -> str:
    """Write a per-instance MATLAB loader file.

    The generated `.m` file is intentionally lightweight: it reads the canonical
    `instance.json`, `metadata.json`, and `planted_solution.csv` files from the same
    folder and returns a struct named `snap`. This avoids duplicating the instance
    data inside MATLAB code while still allowing a non-Python user to load every
    generated instance directly from MATLAB.

    Returns the MATLAB function name written to disk.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    instance_id = str(instance.get("metadata", {}).get("instance_id") or output.parent.name)
    function_name = matlab_safe_function_name(instance_id)
    content = f"""function snap = {function_name}()
%{function_name.upper()} Auto-generated MATLAB loader for SNAP instance {instance_id}.
%
% Usage from MATLAB:
%   addpath('{output.parent.as_posix()}')
%   snap = {function_name}();
%
% Returned fields:
%   snap.instance         Raw decoded JSON structure from instance.json
%   snap.metadata         Raw decoded JSON structure from metadata.json
%   snap.schedule         Table loaded from planted_solution.csv
%   snap.sets             Sets I, D, W, H, S, T, K
%   snap.groups           Groups table, representing set I
%   snap.courses          Courses table, representing set D
%   snap.wards            Wards table, representing set W
%   snap.hospitals        Hospitals table, representing set H
%   snap.params           Raw model_parameters structure
%   snap.B, snap.Du, ...  Convenience tables for model parameters
%
% Notes:
%   - instance.json remains the canonical machine-readable file.
%   - This file is generated only to simplify MATLAB inspection and loading.
%   - The set I is interpreted as student groups, not individual students.

    here = fileparts(mfilename('fullpath'));

    instancePath = fullfile(here, 'instance.json');
    metadataPath = fullfile(here, 'metadata.json');
    schedulePath = fullfile(here, 'planted_solution.csv');

    if ~isfile(instancePath)
        error('SNAP:MissingFile', 'Cannot find instance.json next to this loader.');
    end
    if ~isfile(metadataPath)
        error('SNAP:MissingFile', 'Cannot find metadata.json next to this loader.');
    end
    if ~isfile(schedulePath)
        error('SNAP:MissingFile', 'Cannot find planted_solution.csv next to this loader.');
    end

    snap = struct();
    snap.instance_id = '{instance_id}';
    snap.instance_folder = here;
    snap.instance = jsondecode(fileread(instancePath));
    snap.metadata = jsondecode(fileread(metadataPath));
    snap.schedule = readtable(schedulePath, 'TextType', 'string');

    snap.sets = snap.instance.sets;
    snap.groups = localStructArrayToTable(snap.instance.groups);
    snap.courses = localStructArrayToTable(snap.instance.courses);
    snap.wards = localStructArrayToTable(snap.instance.wards);
    snap.hospitals = localStructArrayToTable(snap.instance.hospitals);
    snap.time = snap.instance.time;
    snap.params = snap.instance.model_parameters;

    % Convenience aliases matching the mathematical model notation.
    snap.B = localStructArrayToTable(snap.params.B);
    snap.Du = localStructArrayToTable(snap.params.Du);
    snap.O = localStructArrayToTable(snap.params.O);
    snap.Mea = localStructArrayToTable(snap.params.Mea);
    snap.PW = localStructArrayToTable(snap.params.PW);
    snap.Dur = localStructArrayToTable(snap.params.Dur);
    snap.weeks = localStructArrayToTable(snap.params.weeks);
    snap.Cap = localStructArrayToTable(snap.params.Cap);
    snap.Com = localStructArrayToTable(snap.params.Com);
    snap.Comm = localStructArrayToTable(snap.params.Comm);
    snap.Av = localStructArrayToTable(snap.params.Av);
    snap.Avb = localStructArrayToTable(snap.params.Avb);
    snap.ne = localStructArrayToTable(snap.params.ne);
    snap.nt = localStructArrayToTable(snap.params.nt);
    snap.nee = localStructArrayToTable(snap.params.nee);
    snap.Eb = localStructArrayToTable(snap.params.Eb);

    % Frequently used fixed time values.
    snap.S = snap.sets.S;
    snap.T = snap.sets.T;
    snap.K = snap.sets.K;
end

function tbl = localStructArrayToTable(value)
%LOCALSTRUCTARRAYTOTABLE Convert JSON-decoded struct arrays to MATLAB tables.
    if isempty(value)
        tbl = table();
        return;
    end
    if istable(value)
        tbl = value;
        return;
    end
    if isstruct(value)
        tbl = struct2table(value);
        return;
    end
    tbl = table(value);
end
"""
    output.write_text(content, encoding="utf-8")
    return function_name
