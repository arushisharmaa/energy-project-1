# Cache Simulator

This is a cache simulator written in Python that simulates the behavior of an L1 cache, L2 cache, and DRAM memory subsystem based on memory trace files.

Here is a link to our report with more details: https://docs.google.com/document/d/1MnymevvOJSRQI9yqrvzd6Hs_3ozKfGV84ti3b6q9F4w/edit?usp=sharing


## Installation

To run the cache simulator, follow these steps:

1. Clone this repository to your local machine:

git clone <repository_url>


2. Install the required dependencies using pip:

pip install unlzw numpy


3. Make sure you have the right permissions for the run.sh file.
   
chmod +x run.sh

4. Run the file to get the output for the 15 trace files.

 ./run.sh     



## Usage

The cache simulator accepts memory trace files in hexadecimal format. Each line in the trace file represents a memory access operation, with the first column indicating the operation type (0: read data, 1: write data, 2: read instruction), and the second column containing the memory address.

## Overview

The cache simulator consists of three main components:

1. **L1 Cache**: Simulates a level 1 cache with separate caches for instructions and data. The L1 cache is designed as a direct-mapped cache.

2. **L2 Cache**: Simulates a level 2 cache that serves as a victim cache for the L1 cache. The L2 cache is designed as a set-associative cache.

3. **DRAM Memory**: Simulates the main memory subsystem. Memory accesses that miss in both the L1 and L2 caches result in accesses to the DRAM memory.

## Results

After running the cache simulator, you will receive output detailing the energy consumption and performance metrics of the simulated cache hierarchy.

## Contributors

- Anvi Bajpai
- Arushi Sharma
