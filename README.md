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


## Output 

Each trace file is individually processed, with metrics averaged over 10 simulation runs. By running the file, the following results for all 15 trace files will be displayed in the console. The mean total energy consumption of the system is calculated, considering contributions from the L1 cache, L2 cache, and DRAM. Additionally, the mean average total active time across all components indicates the duration of active processing during the simulation. 
For the L1 cache, metrics in the output include the mean number of cache hits and misses, time active, number of accesses (hits + misses), and the hit-to-miss ratio. Both dynamic and idle energy consumptions for L1, as well as their totals, are also displayed in the results. The standard deviation for these metrics across the 10 simulations are also output.
Similarly, the L2 cache metrics cover hit-and-miss counts, access counts, active time, hit-to-miss ratios, and dynamic/idle/total energy consumption. For all of these stats, mean and standard deviation across 10 runs are shown. The DRAM access metrics highlight the standard deviation and mean of the number of accesses to DRAM and the associated total energy consumption


## Results

After running the cache simulator, you will receive an output detailing the energy consumption and performance metrics of the simulated cache hierarchy.

## Contributors

- Anvi Bajpai
- Arushi Sharma
