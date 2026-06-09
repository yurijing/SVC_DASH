# Test Instructions

## Running Tests

```bash
# Install test dependencies
python3 -m pip install pytest pytest-cov

# Run all tests
python3 -m pytest tests/ -v

# Run a specific test file
python3 -m pytest tests/strategy/test_qlearning.py -v

# Run with coverage report
python3 -m pytest --cov=strategy --cov=ParseMpd --cov=svc_merge tests/ --cov-report=term
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── strategy/
│   ├── test_utils.py        # find_highest_available_layer
│   ├── test_fixed.py        # FixedQualityStrategy
│   ├── test_threshold.py    # ThresholdStrategy
│   └── test_qlearning.py    # QLearningStrategy
├── test_parse_mpd.py        # ParseMpd MPD XML parser
└── test_svc_merge.py        # NAL unit operations (countNalus, mux)
```
