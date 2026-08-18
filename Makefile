.PHONY: test typecheck complexity mutmut check

test:
	pytest

typecheck:
	mypy src/doomface

complexity:
	radon cc src/doomface -s
	xenon --max-absolute B --max-modules A --max-average A src/doomface

mutmut:
	mutmut run
	mutmut results

check: test typecheck complexity mutmut
