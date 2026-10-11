.PHONY: run bench test install

# Install all backend and frontend dependencies
install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install && npm run build

# Single-command start for backend and frontend together
run:
	python run_server.py

# Run standalone benchmark suite and generate measurements
bench:
	python run_bench.py

# Run unit tests and hypothesis property verification
test:
	python -m pytest backend/app/tests/test_unit.py -v
