.PHONY: run bench test install integrity demo-check

# Install all backend and frontend dependencies
install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install && npm run build

# Single-command start for backend and frontend together
run:
	python run_server.py

# One-command benchmark: measures everything, writes bench/results.*
bench:
	python scripts/bench.py

# End-to-end demo check: upload -> allocate -> export -> check (exit 0 = demo works)
demo-check:
	python scripts/demo_check.py

# Run unit tests and hypothesis property verification
test:
	python -m pytest backend/app/tests/test_unit.py -v

# Integrity guard: fail if any fabricated metric literal is (re-)introduced
integrity:
	python -m pytest backend/app/tests/test_integrity.py -v
