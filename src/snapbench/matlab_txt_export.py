from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .matlab_export import matlab_safe_function_name


SETS = ["I", "D", "W", "H", "S", "T", "K"]
PARAMETERS = ["mem", "semester", "Du", "O", "PW", "Dur", "weeks", "Cap", "ne", "nee", "nt"]
TABLES = ["B", "Mea", "Comm", "Com", "Eb", "Av", "Avb"]


def write_matlab_txt_loader(root: str | Path, instance: Dict[str, Any]) -> None:
    """Write MATLAB loaders that read the per-symbol TXT export into a struct."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    instance_id = str(instance.get("metadata", {}).get("instance_id", "instance"))
    safe_name = matlab_safe_function_name(instance_id)
    wrapper_name = f"{safe_name}.m"

    content = f"""function snap = load_instance()
%LOAD_INSTANCE Load this SNAP instance from TXT/JSON files into a MATLAB struct.
%
% Usage:
%   addpath('M')
%   snap = load_instance();
%
% The loader reads ../txt, ../instance.json, ../metadata.json, and
% ../planted_solution.csv. The returned struct contains tables for every set,
% parameter, and binary table used by the mathematical model.

    here = fileparts(mfilename('fullpath'));
    instanceRoot = fileparts(here);
    txtRoot = fullfile(instanceRoot, 'txt');

    snap = struct();
    snap.instance_id = '{instance_id}';
    snap.instance_folder = instanceRoot;

    snap.instance = jsondecode(fileread(fullfile(instanceRoot, 'instance.json')));
    snap.metadata = jsondecode(fileread(fullfile(instanceRoot, 'metadata.json')));
    snap.schedule = readtable(fullfile(instanceRoot, 'planted_solution.csv'), 'TextType', 'string');

    snap.sets = struct();
    snap.params = struct();
    snap.tables = struct();

    % Sets
    snap.sets.I = localReadSet(fullfile(txtRoot, 'sets', 'I.txt'));
    snap.sets.D = localReadSet(fullfile(txtRoot, 'sets', 'D.txt'));
    snap.sets.W = localReadSet(fullfile(txtRoot, 'sets', 'W.txt'));
    snap.sets.H = localReadSet(fullfile(txtRoot, 'sets', 'H.txt'));
    snap.sets.S = localReadSet(fullfile(txtRoot, 'sets', 'S.txt'));
    snap.sets.T = localReadSet(fullfile(txtRoot, 'sets', 'T.txt'));
    snap.sets.K = localReadSet(fullfile(txtRoot, 'sets', 'K.txt'));

    % Parameters
    snap.params.mem = localReadTable(fullfile(txtRoot, 'parameters', 'mem.txt'));
    snap.params.semester = localReadTable(fullfile(txtRoot, 'parameters', 'semester.txt'));
    snap.params.Du = localReadTable(fullfile(txtRoot, 'parameters', 'Du.txt'));
    snap.params.O = localReadTable(fullfile(txtRoot, 'parameters', 'O.txt'));
    snap.params.PW = localReadTable(fullfile(txtRoot, 'parameters', 'PW.txt'));
    snap.params.Dur = localReadTable(fullfile(txtRoot, 'parameters', 'Dur.txt'));
    snap.params.weeks = localReadTable(fullfile(txtRoot, 'parameters', 'weeks.txt'));
    snap.params.Cap = localReadTable(fullfile(txtRoot, 'parameters', 'Cap.txt'));
    snap.params.ne = localReadTable(fullfile(txtRoot, 'parameters', 'ne.txt'));
    snap.params.nee = localReadTable(fullfile(txtRoot, 'parameters', 'nee.txt'));
    snap.params.nt = localReadTable(fullfile(txtRoot, 'parameters', 'nt.txt'));

    % Binary tables / incidence parameters
    snap.tables.B = localReadTable(fullfile(txtRoot, 'tables', 'B.txt'));
    snap.tables.Mea = localReadTable(fullfile(txtRoot, 'tables', 'Mea.txt'));
    snap.tables.Comm = localReadTable(fullfile(txtRoot, 'tables', 'Comm.txt'));
    snap.tables.Com = localReadTable(fullfile(txtRoot, 'tables', 'Com.txt'));
    snap.tables.Eb = localReadTable(fullfile(txtRoot, 'tables', 'Eb.txt'));
    snap.tables.Av = localReadTable(fullfile(txtRoot, 'tables', 'Av.txt'));
    snap.tables.Avb = localReadTable(fullfile(txtRoot, 'tables', 'Avb.txt'));

    % Convenience aliases matching the mathematical notation.
    snap.I = snap.sets.I; snap.D = snap.sets.D; snap.W = snap.sets.W; snap.H = snap.sets.H;
    snap.S = snap.sets.S; snap.T = snap.sets.T; snap.K = snap.sets.K;
    snap.mem = snap.params.mem; snap.Du = snap.params.Du; snap.O = snap.params.O; snap.PW = snap.params.PW;
    snap.Dur = snap.params.Dur; snap.weeks = snap.params.weeks; snap.Cap = snap.params.Cap;
    snap.B = snap.tables.B; snap.Mea = snap.tables.Mea; snap.Comm = snap.tables.Comm; snap.Com = snap.tables.Com;
    snap.Eb = snap.tables.Eb; snap.Av = snap.tables.Av; snap.Avb = snap.tables.Avb;
end

function values = localReadSet(path)
    tbl = readtable(path, 'FileType', 'text', 'Delimiter', '\t', 'TextType', 'string');
    values = tbl{{:,1}};
end

function tbl = localReadTable(path)
    tbl = readtable(path, 'FileType', 'text', 'Delimiter', '\t', 'TextType', 'string');
end
"""
    (root / "load_instance.m").write_text(content, encoding="utf-8")
    wrapper = f"""function snap = {safe_name}()
%{safe_name.upper()} Instance-specific wrapper around load_instance().
    snap = load_instance();
end
"""
    (root / wrapper_name).write_text(wrapper, encoding="utf-8")
    (root / "README_MATLAB.txt").write_text(
        "MATLAB loader files\n\n"
        "Use from the instance folder or add the M folder to path:\n"
        "    addpath('M')\n"
        "    snap = load_instance();\n\n"
        f"Instance-specific wrapper:\n    snap = {safe_name}();\n\n"
        "The loader reads tab-delimited TXT files from ../txt and returns a struct with sets, params, and tables.\n",
        encoding="utf-8",
    )
