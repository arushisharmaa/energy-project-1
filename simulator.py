import random
import unlzw
import os
import numpy as np

clock = 0

class l1_cache:
    L1_RW_TIME = .5 * (10 ** -9)  # Time taken to access the memory (in ns) convert from nS to seconds 
    NUM_LINES = 32768 // 64  # size = 32KB for instructions and 32KB for data / cache line size is 64 bytes? because it's direct mapped. access simultaneously
    L1_IDLE = .5  # Idle power consumption of the memory (in watts)
    L1_RW = 1  # value during reads or writes
    L2_ENERGY_PENALTY =  5 * (10 ** -12) # Energy penalty for accessing the memory (in joules) convert from pJ to J 

    def __init__(self, l2):
        # Set up empty cache
        self.l2 = l2
        self.l1_active_time = 0
        self.l1_hits = 0  # Number of misses stored in L1
        self.l1_misses = 0  # Number of hits stored in L1
        self.l1_access = 0 # Number of accesses in L1 
        self.l1_energy = 0  # Total energy consumed by the cache in joules
        self.instruction_cache = [{'tag': None, 'dirty': False, 'address': None} for _ in range(self.NUM_LINES)]
        self.data_cache = [{'tag': None, 'dirty': False, 'address': None} for _ in range(self.NUM_LINES)]

    def l1_read_data(self, address):
        # Reading -> add in the read/write time to the active time
        self.l1_active_time += self.L1_RW_TIME
        self.l1_access += 1
        global clock
        clock += self.L1_RW_TIME 

        tag_bit = format(address, '032b')[:17]  # First 17 bits of the file are the tag formatted into 32 bits
        idx_bit = int(format(address, '032b')[17:26], 2)  # From 17 to 26 is the index formatted into 32 bits

        # Update energy
        self.l1_energy += self.L1_RW_TIME
        # Check if the data is in the cache
        did_hit = False
        if self.data_cache[idx_bit]['tag'] != tag_bit:
            self.l1_misses += 1

            #get instr from L2
            self.l2.l2_read(address) 

            # Update the cache state with fetched data; write back so no need to write to L2 yet
            self.data_cache[idx_bit].update({'tag': tag_bit, 'dirty': True, 'address': address})
            did_hit = False
        else:
            self.l1_hits += 1
            did_hit = True

        # Return whether it's a hit or miss
        return did_hit  

    def l1_read_instruction(self, address):
        # Reading -> add in the read/write time to the active time
        self.l1_active_time += self.L1_RW_TIME
        self.l1_access += 1
        global clock
        clock += self.L1_RW_TIME 

        tag_bit = format(address, '032b')[:17]  # First 17 bits of the file are the tag formatted into 32 bits
        idx_bit = int(format(address, '032b')[17:26], 2)  # From 17 to 26 is the index formatted into 32 bits

        # Update energy
        self.l1_energy += self.L1_RW_TIME

        did_hit = False
        # Check if the instruction is in the cache
        if self.instruction_cache[idx_bit]['tag'] != tag_bit:
            self.l1_misses += 1
            #get instruction data from l2
            self.l2.l2_read(address)
            self.instruction_cache[idx_bit].update({'tag': tag_bit, 'dirty': True, 'address': address})
            did_hit = False
        else:
            self.l1_hits += 1
            did_hit = True

        # Return whether it's a hit or miss
        return did_hit
    
    def writeback(self, address):
        # Writing -> add in the read/write time to the active time 
        self.l1_active_time += self.L1_RW_TIME 
        
        tag_bit = format(address, '032b')[:17]  # First 17 bits of the file are the tag formatted into 32 bits
        idx_bit = int(format(address, '032b')[17:26], 2)  # From 17 to 26 is the index formatted into 32 bits

        self.l1_energy += self.L1_RW_TIME
     
        did_hit = False
        # Check if the data is in the cache
        if self.data_cache[idx_bit]['tag'] != tag_bit:
            # Cache miss
            self.l1_misses += 1

            # Read the data from the L2 cache//which reads from dram if data is not in l2 either
            self.l2.l2_read(address)

            if self.data_cache[idx_bit]['dirty']:
                # If the cache line being replaced is dirty, write its contents back to the L2 cache
                self.l2.write(address)
            # Update the cache line with the new data and mark it as dirty
            self.data_cache[idx_bit].update({'tag': tag_bit, 'dirty': True, 'address': address})
        else:
            # Cache hit
            self.l1_hits += 1
            # Mark the cache line as dirty
            self.data_cache[idx_bit]["dirty"] = True
            did_hit = True

        return did_hit


class l2_cache:
    L2_RW_TIME = 5 * (10 ** -9)  # Time taken to access the memory (in ns) convert from nS to seconds 
    L2_IDLE = 0.8 # Idle power consumption of the memory (in watts)
    L2_RW = 2 #Value during reads or writes
    L2_ENERGY_PENALTY =  5 * (10 ** -12) # Energy penalty for accessing the memory (in joules) convert from pJ to J 
    SIZE = 262144 #size = 256KB -> combined cache converted into bytes 
    LINE_SIZE = 64 #cache line size is 64 bytes
    DRAM_PENALTY = 640 * (10 ** -12)  # Energy penalty for accessing the memory (in joules) convert from pJ to J 
    
    def __init__(self, associativity, DRAM):
        self.DRAM = DRAM
        self.num_sets = self.SIZE // (self.LINE_SIZE * associativity)  # Number of sets
        self.associativity = associativity 
        self.l2_active_time = 0
        self.l2_hits = 0  # Total number of hits 
        self.l2_access = 0  #Total number of accesses 
        self.l2_misses = 0  # Total number of misses 
        self.l2_energy = 0  # Total energy consumed for L2 in J 

        # Initialize cache as empty
        self.cache = [[{'tag': None, 'dirty': False} for _ in range(associativity)] for _ in range(self.num_sets)]

    def l2_read(self, address):
        #reading -> add in the read/write time to the active time 
        self.l2_active_time += self.L2_RW_TIME 
        self.l2_access += 1
        global clock
        clock += self.L2_RW_TIME 

        tag_bit = format(address, '032b')[:16]
        idx_bit = int(format(address, '032b')[16:26], 2)
        
        self.l2_energy += self.L2_RW_TIME * self.L2_RW + self.L2_ENERGY_PENALTY

        did_hit = True
        # Check if the data is in the cache
        if any(line['tag'] == tag_bit for line in self.cache[idx_bit]):
            self.l2_hits += 1
        else:
            # Cache miss
            self.l2_misses += 1
            did_hit = False

            #fetch data from dram
            self.DRAM.dram_read()

            # Find an empty line or evict a line
            empty_line = next((line for line in self.cache[idx_bit] if line['tag'] is None), None)
            if empty_line:
                empty_line['tag'] = tag_bit
                empty_line['dirty'] = True
            else: 
                evict_index = random.randint(0, self.associativity - 1)
                evict_line = self.cache[idx_bit][evict_index]
                if evict_line['dirty']:
                    # Writebackto DRAM before updating cache
                    self.DRAM.dram_write()
                evict_line['tag'] = tag_bit 
                evict_line['dirty'] = True
        return did_hit

    def write(self, address):
        #writing -> add in the read/write time to the active time 
        self.l2_active_time += self.L2_RW_TIME 
        self.l2_access += 1
        
        tag_bit = format(address, '032b')[:16]
        idx_bit = int(format(address, '032b')[16:26], 2)
        self.l2_energy += self.L2_RW_TIME * self.L2_RW + self.L2_ENERGY_PENALTY

        # Check if the data is in the cache
        for _, line in enumerate(self.cache[idx_bit]):
            if line['tag'] == tag_bit:
                self.l2_hits += 1
                line['dirty'] = True
                return True

        # Cache miss access data from next level in the memory hierarchy (DRAM)
        self.l2_misses += 1
        self.DRAM.dram_read()

        # Find an empty line or evict a line
        empty_line = next((line for line in self.cache[idx_bit] if line['tag'] is None), None)
        if empty_line:
            empty_line['tag'] = tag_bit 
            empty_line['dirty'] = True
        else:
            evict_index = random.randint(0, self.associativity - 1)
            evict_line = self.cache[idx_bit][evict_index]
            if evict_line['dirty']:
                # Writeback to DRAM on eviction from L2 cache
                self.DRAM.dram_write()
            evict_line['tag'] = tag_bit 
            evict_line['dirty'] = True
        return False

class dram_mem:
# Constants
    DRAM_PENALTY = 640 * (10 ** -12)  # Energy penalty for accessing the memory (in joules) convert from pJ to J 
    IDLE_W = 0.8  # Idle power consumption of the memory (in watts)
    RW_W = 4  # Power consumption during read or write operations (in watts)
    ACTIVE = 45 * (10 ** -9)  # Time taken to access the memory (in ns) convert from nS to seconds 
    
    def __init__(self): 
        self.dynamic_energy = 0  # Accumulated dynamic energy consumption during accesses
        self.active_time = 0
        self.dram_access_val = 0 

    #Everytime dram is accessed, increment time active, total penalty, and dynamic energy consumed
    def dram_read(self):
        global clock 
        clock += self.ACTIVE
        self.active_time += self.ACTIVE 
        self.dynamic_energy += self.RW_W * self.ACTIVE + self.DRAM_PENALTY
        self.dram_access_val += 1

    def dram_write(self):
        self.active_time += self.ACTIVE 
        self.dynamic_energy += self.RW_W * self.ACTIVE + self.DRAM_PENALTY
        self.dram_access_val += 1


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
    l1_hits = []
    l1_access = [] 
    l1_misses = []
    l2_hits = []
    l2_misses = []
    l2_access = [] 
    l1_dynamic_energy = []
    l1_idle_energy = []
    l2_dynamic_energy = []
    l2_idle_energy = []
    dram_dynamic_energy  = []
    dram_idle_energy = []
    dram_access = [] 
    active_times = []


    for _ in range(10):
        # Initialize components for each file
        dram = dram_mem()
        l2 = l2_cache(4, dram) #change the first value for associativty 
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
                if operation  == '0': 
                    l1.l1_read_data(address)
                #1 for memory write 
                elif operation  == '1':
                    l1.writeback(address)
                #2 for instruction fetch 
                elif operation  == '2':
                    l1.l1_read_instruction(address)
                #don't have anything for ignore flush 
                elif operation == '3' or operation == '4': 
                    pass
                
        # Store metrics for each trace file run
        l1_hits.append(l1.l1_hits)
        l1_misses.append(l1.l1_misses)
        l1_access.append(l1.l1_access)
        l1_hits_misses.append(l1.l1_hits / (l1.l1_hits + l1.l1_misses))

        l2_hits.append(l2.l2_hits)
        l2_misses.append(l2.l2_misses)
        l2_hits_misses.append(l2.l2_hits / (l2.l2_hits + l2.l2_misses))
        l2_access.append(l2.l2_access)

        l1_dynamic_energy.append(l1.l1_energy)
        l1_idle_energy.append(l1.L1_IDLE * clock * 2)
        l2_dynamic_energy.append(l2.l2_energy)
        l2_idle_energy.append(l2.L2_IDLE * clock)
        active_times.append(l1.l1_active_time + l2.l2_active_time + dram.active_time)

        dram_access.append(dram.dram_access_val)
        dram_idle_energy.append(dram.IDLE_W * clock)
        dram_dynamic_energy.append(dram.dynamic_energy) 

    total_energy = np.mean(np.array(l1_idle_energy) + np.array(l1_dynamic_energy) + np.array(l2_idle_energy) + np.array(l2_dynamic_energy) + np.array(dram_idle_energy) + np.array(dram_dynamic_energy))
    
    data = {
    "trace file": trace_file,
    "Total Energy": total_energy,
    "Mean Average Total Active Time": np.mean(active_times),
    "Number of L1 Hits (MEAN)": np.mean(l1_hits),
    "Number of L1 Hits (SD)": np.std(l1_hits),
    "Number of L1 Misses (MEAN)": np.mean(l1_misses),
    "Number of L1 Misses (SD)": np.std(l1_misses),
    "Number of L1 Access (MEAN)": np.mean(l1_access),
    "Number of L1 Access (SD)": np.std(l1_access),
    "L1 Hit:Miss (MEAN)": np.mean(l1_hits_misses),
    "L1 Hit:Miss (SD)": np.std(l1_hits_misses),
    "L1 Total Energy (MEAN)": np.mean(np.sum([l1_dynamic_energy, l1_idle_energy], axis=0)),
    "L1 Total Energy (SD)": np.std(np.sum([l1_dynamic_energy, l1_idle_energy], axis=0)),
    "Number of L2 Hits (MEAN)": np.mean(l2_hits),
    "Number of L2 Hits (SD)": np.std(l2_hits),
    "Number of L2 Misses (MEAN)": np.mean(l2_misses),
    "Number of L2 Misses (SD)": np.std(l2_misses),
    "Number of L2 Access (MEAN)": np.mean(l2_access),
    "Number of L2 Access (SD)": np.std(l2_access),
    "L2 Hit:Miss (MEAN)": np.mean(l2_hits_misses),
    "L2 Hit:Miss (SD)": np.std(l2_hits_misses),
    "L2 Total Energy (MEAN)": np.mean(np.sum([l2_dynamic_energy, l2_idle_energy], axis=0)),
    "L2 Total Energy (SD)": np.std(np.sum([l2_dynamic_energy, l2_idle_energy], axis=0)),
    "Number of DRAM Access (MEAN)": np.mean(dram_access),
    "Number of DRAM Access (SD)": np.std(dram_access),
    "DRAM Total Energy (MEAN)": np.mean(np.sum([dram_dynamic_energy, dram_idle_energy], axis=0)),
    "DRAM Total Energy (SD)": np.std(np.sum([dram_dynamic_energy, dram_idle_energy], axis=0))
}
    # Join all values into a single string
    data_str = ",".join(map(str, data.values()))

    # Print the single string
    print(data_str)



# Run the simulation for each trace file
trace_files = ["008.espresso.din.Z", "013.spice2g6.din.Z", "015.doduc.din.Z", "022.li.din.Z", "023.eqntott.din.Z", "026.compress.din.Z", "034.mdljdp2.din.Z", "039.wave5.din.Z", "047.tomcatv.din.Z", "048.ora.din.Z", "085.gcc.din.Z", "089.su2cor.din.Z", "090.hydro2d.din.Z", "093.nasa7.din.Z", "094.fpppp.din.Z"]
for file in trace_files:
    active_time = 0
    trace(file)
