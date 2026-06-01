PATTERNS = {
    "python": r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\w+)',
    "javascript": r'at (?P<func>(?:new\s+)?\S+) \((?P<file>[^:]+):(?P<line>\d+):\d+\)',
    "java": r'at (?P<func>[^\(]+)\((?P<file>[^:]+):(?P<line>\d+)\)',
    "dart": r'#\d+\s+(?P<func>\S+) \((?P<file>(?:package:)?[^:)]+):(?P<line>\d+):\d+\)',
}
