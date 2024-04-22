import random
import unlzw
import os
import numpy as np

active_time = 0

class l1_cache:
    L1_RW_TIME = .5 * (10 ** -9)  # Time taken to access the memory (in ns) convert from nS to seconds 
    NUM_LINES = 32768 // 64 #size = 32KB for instructions and 32KB for data / cache line size is 64 bytes? because it's direct mapped. access simultaneously
    L1_IDLE = .5  # Idle power consumption of the memory (in watts)
    L1_RW = 1 # value during reads or writes
    
    def __init__(self, l2):
        #set up empty cache 
        self.l2 = l2
        self.instruction_cache = [None] * self.NUM_LINES
        for i in range(self.NUM_LINES):
            self.instruction_cache[i] = {'tag': None, 'dirty': False, 'address': None}

        # Initialize data cache as empty
        self.data_cache = [None] * self.NUM_LINES
        for i in range(self.NUM_LINES):
            self.data_cache[i] = {'tag': None, 'dirty': False, 'address': None}

        self.l1_hits = 0 #Number of misses stored in L1 
        self.l1_misses = 0 #Number of hits stored in L1 
        self.l1_energy = 0  # Total energy consumed by the cache in joules

    def l1_read_data(self, address):
        global active_time
        active_time += self.L1_RW_TIME
        
        addy = format(address, '032b')
        tag = addy[:17]  # first 17 bits of the file are the tag formatted into 32 bits
        idx = int(addy[17:26], 2)  # from 17 to 26 is the index formatted into 32 bits 

        # Update energy
        self.l1_energy += self.L1_RW 
        
        # Check if the data is in the cache
        did_hit = False
        if self.data_cache[idx]['tag'] == tag:
            self.l1_hits += 1
            did_hit = True
        else:
            self.l1_misses += 1
            # Access data from L2 cache
            l2_hit = self.l2.l2_read(address)
            if not l2_hit:
                self.l2.writethrough(address)
            # Fetch the data from L2 cache and update L1 cache
            self.data_cache[idx]['tag'] = tag
            self.data_cache[idx]['address'] = address
            self.data_cache[idx]['dirty'] = False
            did_hit = False

        # Return whether it's a hit or miss
        return did_hit
    

    def l1_read_instruction(self, address):
        global active_time
        active_time += self.L1_RW_TIME 

        addy = format(address, '032b')
        tag = addy[:17] #first 17 bits of the file are the tag formated into 32 bits 
        idx = int(addy[17:26], 2) #from 17 to 26 is the index formated into 32 bits 

        # Update energy
        self.l1_energy += self.L1_RW 

        did_hit = False
        # Check if the instruction is in the cache
        if self.instruction_cache[idx]['tag'] == tag:
            self.l1_hits += 1
            did_hit = True
        else:
            self.l1_misses += 1
            l2_hit = self.l2.l2_read(address)
            if not l2_hit:
                self.l2.writethrough(address)
            self.instruction_cache[idx]['tag'] = tag
            self.instruction_cache[idx]['address'] = address
            self.instruction_cache[idx]['dirty'] = False
            did_hit = False

        # Return whether it's a hit or miss
        return did_hit
    
    def writeback(self, address):
        # Extract tag and set index bits from the memory address
        global active_time
        active_time += self.L1_RW_TIME

        addy = format(address, '032b')
        tag = addy[:17]  # first 17 bits of the file are the tag formatted into 32 bits
        idx = int(addy[17:26], 2)  # from 17 to 26 is the index formatted into 32 bits

        self.l1_energy += self.L1_RW

        # Check if the data is in the cache
        if self.data_cache[idx]['tag'] == tag:
            self.l1_hits += 1
            self.data_cache[idx]["dirty"] = True
            #immediately write to l2 as well
            self.l2.writethrough(address)
            return True

        # Cache miss
        self.l1_misses += 1
        # if cache line not empty, write to l2 then write to line / mark as dirty
        if self.data_cache[idx]['dirty']:
            # Write to L2 before changing data
            self.l2.writethrough(address)

        #for getting data//not dealing with it in this code...
        self.l2.l2_read(address)
        self.data_cache[idx]['tag'] = tag
        self.data_cache[idx]['dirty'] = True
        return False


class l2_cache:
    L2_RW_TIME = 5 * (10 ** -9)  # Time taken to access the memory (in ns) convert from nS to seconds 
    L2_IDLE = 0.8 # Idle power consumption of the memory (in watts)
    L2_RW = 2 #Value during reads or writes
    L2_ENERGY_PENALTY =  5 * (10 ** -12) # Energy penalty for accessing the memory (in joules) convert from pJ to J 
    SIZE = 262144 #size = 256KB -> combined cache converted into bytes 
    LINE_SIZE = 64 #cache line size is 64 bytes
    
    def __init__(self, associativity, DRAM):
        self.DRAM = DRAM
        self.num_sets = self.SIZE // (self.LINE_SIZE * associativity)  # Number of sets
        self.associativity = associativity 
        # Make the cache empty 
        self.cache = [None] * self.num_sets
        for i in range(self.num_sets):
            #go through each level of associativity 
            self.cache[i] = [{'tag': None, 'dirty': False} for _ in range(associativity)]
        
        self.l2_hits = 0 # Total number of hits 
        self.l2_misses = 0 # Total number of misses 
        self.l2_energy = 0  # Total energy consumed by the cache in joules

    def l2_read(self, address):
        # Extract tag and set index bits from the memory address
        global active_time
        active_time += self.L2_RW_TIME 

        addy = format(address, '032b')
        tag = addy[:16]
        idx = int(addy[16:26], 2)
        
        # Check if the data is in the cache
        for line in self.cache[idx]:
            if line['tag'] == tag:
                self.l2_hits += 1
                self.l2_energy += self.L2_RW_TIME  * self.L2_RW 
                return True
        
        # Cache miss
        self.l2_misses += 1

        # See if any lines are empty
        for line in self.cache[idx]:
            if line['tag'] == None:
                self.l2_energy += self.L2_RW_TIME  * self.L2_RW + self.L2_ENERGY_PENALTY
                line['tag'] = tag
                line['dirty'] = True
                return False

        evict = random.randint(0, self.associativity - 1)
        if self.cache[idx][evict]['dirty']:
            # write to dram before updating cache
            self.DRAM.dram_access()
        self.cache[idx][evict]['tag'] = tag
        self.cache[idx][evict]['dirty'] = False
        return False

    def writethrough(self, address):
        # Extract tag and set index bits from the memory address
        global active_time
        active_time += self.L2_RW_TIME

        addy = format(address, '032b')
        tag = addy[:16]
        idx = int(addy[16:26], 2)

        # Check if the data is in the cache
        for line in self.cache[idx]:
            if line['tag'] == tag:
                self.l2_hits += 1
                self.l2_energy += self.L2_RW_TIME  * self.L2_RW 
                line['dirty'] = True
                return True

        # Cache miss
        self.l2_misses += 1
        
        # Access data from next level in the memory hierarchy (DRAM)
        self.DRAM.dram_access()
        
        # See if any lines are empty
        for line in self.cache[idx]:
            if line['tag'] == None:
                self.l2_energy += self.L2_RW_TIME * self.L2_RW + self.L2_ENERGY_PENALTY
                line['tag'] = tag
                line['dirty'] = True
                return False

        evicting_index = random.randint(0, self.associativity - 1)
        if self.cache[idx][evicting_index]['dirty']:
            # Writethrough to DRAM on eviction from L2 cache
            self.DRAM.dram_access()
        self.cache[idx][evicting_index]['tag'] = tag
        self.cache[idx][evicting_index]['dirty'] = True
        return False

class dram_mem:
# Constants
    DRAM_PENALTY = 640 * (10 ** -12)  # Energy penalty for accessing the memory (in joules) convert from pJ to J 
    IDLE_W = 0.8  # Idle power consumption of the memory (in watts)
    RW_W = 4  # Power consumption during read or write operations (in watts)
    ACTIVE = 45 * (10 ** -9)  # Time taken to access the memory (in ns) convert from nS to seconds 
    
    def __init__(self): 
        self.dynamic_energy = 0  # Accumulated dynamic energy consumption during accesses
        self.total_dram_penalty = 0  # Accumulated total energy penalty for all accesses
        
    #Everytime dram is accessed, increment time active, total penalty, and dynamic energy consumed
    def dram_access(self):
        global active_time
        active_time += self.ACTIVE 
        self.total_dram_penalty += self.DRAM_PENALTY
        self.dynamic_energy += self.RW_W * self.ACTIVE


def trace(trace_file):
    BASE = 16 
    
    #Used this to understand how to trace and unzip a file like this -> https://stackoverflow.com/questions/32921263/uncompressing-a-z-file-with-python 
    # Check if the trace file has a .Z extension
    if trace_file.endswith('.Z'):
        # Decompress the .Z file
        decompressed_file_path = trace_file[:-2]
        with open(decompressed_file_path, 'wb') as f_out, open(trace_file, 'rb') as f_in:
            f_out.write(unlzw.unlzw(f_in.read()))
        
        # Open the decompressed file for reading
        trace_file = decompressed_file_path

    # Initialize lists to store energy consumption and hit/miss ratios
    l1_hits_misses = []
    l2_hits_misses = []
    l1_dynamic_energy = []
    l1_idle_energy = []
    l2_dynamic_energy = []
    l2_idle_energy = []
    active_times = []

    for _ in range(10):
        # Initialize components from the 
        dram = dram_mem()
        l2 = l2_cache(4, dram)
        l1 = l1_cache(l2)

        # Reset active time for each run
        global active_time
        active_time = 0

        with open(trace_file, 'r') as f:
            for line in f:
                # global active_time
                active_time += .5 * (10 ** -9) #processor runs at 2GHz (0.5nsec cycle) 
                parts = line.strip().split()
                operation = parts[0]  # Extract the access type (0: read data, 1: write data, 2: read instruction)
                address = int(parts[1], BASE) # Convert the hexadecimal address string to an integer

                #0 for memory 
                if operation  == '0' and (not l1.l1_read_data(address) and not l2.l2_read(address)): 
                    dram.dram_access()
                #1 for memory write 
                elif operation  == '1':
                    l2.writethrough(address)
                #2 for instruction fetch 
                elif operation  == '2' and (not l1.l1_read_instruction(address) and not l2.l2_read(address)):
                    dram.dram_access()
                #don't have anything for ignore flush 
                elif operation == '3' or operation == '4': 
                    pass
                
        # Store metrics for each trace file run
        l1_hits_misses.append(l1.l1_hits / (l1.l1_hits + l1.l1_misses))
        l2_hits_misses.append(l2.l2_hits / (l2.l2_hits + l2.l2_misses))
        l1_dynamic_energy.append(l1.l1_energy)
        l1_idle_energy.append(l1.L1_IDLE * active_time * 2)
        l2_dynamic_energy.append(l2.l2_energy)
        l2_idle_energy.append(l2.L2_IDLE * active_time)
        active_times.append(active_time)

    # Print results for each trace file 
    #print(f"{trace_file} {np.mean(l1_hits_misses)} {np.std(l1_hits_misses)} {np.mean(l2_hits_misses)} {np.std(l2_hits_misses)} {np.mean(l1_dynamic_energy)} {np.std(l1_dynamic_energy)} {np.mean(l1_idle_energy)} {np.std(l1_idle_energy)} {np.mean(np.sum([l1_dynamic_energy, l1_idle_energy], axis=0))} {np.std(np.sum([l1_dynamic_energy, l1_idle_energy], axis=0))} {np.mean(l2_dynamic_energy)} {np.std(l2_dynamic_energy)} {np.mean(l2_idle_energy)} {np.std(l2_idle_energy)} {np.mean(np.sum([l2_dynamic_energy, l2_idle_energy], axis=0))} {np.std(np.sum([l2_dynamic_energy, l2_idle_energy], axis=0))} {np.mean(active_times)}") 
    
    print(trace_file)
    print(f"Mean Average Active Time: {np.mean(active_times)}")
    print(f"L1 HIT:MISS (MEAN): {np.mean(l1_hits_misses)}")
    print(f"L1 HIT:MISS (SD): {np.std(l1_hits_misses)}")
    print(f"L2 HIT:MISS (MEAN): {np.mean(l2_hits_misses)}")
    print(f"L2 HIT:MISS (SD): {np.std(l2_hits_misses)}")
    print(f"L1 ENERGY CONSUMPTION (DYNAMIC) -> (MEAN): {np.mean(l1_dynamic_energy)}")
    print(f"L1 ENERGY CONSUMPTION (DYNAMIC) -> (SD): {np.std(l1_dynamic_energy)}")
    print(f"L1 ENERGY CONSUMPTION (IDLE) -> (MEAN): {np.mean(l1_idle_energy)}")
    print(f"L1 ENERGY CONSUMPTION (IDLE) -> (SD): {np.std(l1_idle_energy)}")
    print(f"L1 TOTAL ENERGY (MEAN): {np.mean(np.sum([l1_dynamic_energy, l1_idle_energy], axis=0))}")
    print(f"L1 TOTAL ENERGY (SD): {np.std(np.sum([l1_dynamic_energy, l1_idle_energy], axis=0))}")
    print(f"L2 ENERGY CONSUMPTION (DYNAMIC) -> (MEAN): {np.mean(l2_dynamic_energy)}")
    print(f"L2 ENERGY CONSUMPTION (DYNAMIC) -> (SD): {np.std(l2_dynamic_energy)}")
    print(f"L2 ENERGY CONSUMPTION (IDLE) -> (MEAN): {np.mean(l2_idle_energy)}")
    print(f"L2 ENERGY CONSUMPTION (IDLE) -> (SD): {np.std(l2_idle_energy)}")
    print("\n")

# Run the simulation for each trace file
trace_files = ["008.espresso.din.Z", "013.spice2g6.din.Z", "015.doduc.din.Z", "022.li.din.Z", "023.eqntott.din.Z", "026.compress.din.Z", "034.mdljdp2.din.Z", "039.wave5.din.Z", "047.tomcatv.din.Z", "048.ora.din.Z", "085.gcc.din.Z", "089.su2cor.din.Z", "090.hydro2d.din.Z", "093.nasa7.din.Z", "094.fpppp.din.Z"]
for file in trace_files:
    active_time = 0
    trace(file)

