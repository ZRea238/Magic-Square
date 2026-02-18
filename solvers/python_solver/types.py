from typing import Optional


Grid = list[list[Optional[int]]]
SolvedGrid = list[list[int]]
TraceLog = list[str]
TraceStep = dict[str, object]
CountResult = dict[str, object]
ProgressState = dict[str, int]
GameMode = str
