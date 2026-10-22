FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends g++ cmake make python3 gcc-avr avr-libc binutils-avr avrdude simavr libsimavr-dev ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
COPY . .
RUN sh scripts/test.sh && cmake -S . -B build/cmake && cmake --build build/cmake && ctest --test-dir build/cmake --output-on-failure && sh scripts/build-avr.sh && sh scripts/build-sim.sh && sh scripts/build-inspector.sh && python3 scripts/verify-sim.py && RUN_AVR_TESTS=1 RUN_CPU_TESTS=1 python3 -m unittest discover -s tests -p "test_*.py"
RUN useradd --uid 10001 --create-home lab
USER lab
EXPOSE 8080
CMD ["python3", "host/server.py", "--bind", "0.0.0.0"]
