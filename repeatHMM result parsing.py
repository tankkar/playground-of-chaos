import matplotlib.pyplot as plt
import re

# Example data
data = ['notch2nlc', 13.0, [14, 15], 'allocr:11:1, 14:2, 15:11, 123:2, 127:2, 131:1, 139:1, 144:1, 163:1, 286:1, 302:1, 312:1,', 25, 17]
data =  ['notch2nlc', 13.0, [14, 15], 'allocr:11:1, 14:2, 15:11, 123:2, 127:2, 131:1, 139:1, 144:1, 163:1, 286:1, 302:1, 312:1,', 25, 17]

# Extract 'allocr' string from the data
allocr_str = data[3]

# Parse the 'allocr' string
allocr_pattern = re.compile(r'(\d+):(\d+)')
matches = allocr_pattern.findall(allocr_str)

# Extract estimated repeat counts and number of long reads
repeat_counts = []
long_reads = []

for match in matches:
    repeat_count, long_read = map(int, match)
    repeat_counts.append(repeat_count)
    long_reads.append(long_read)

# Plotting
plt.figure(figsize=(10, 6))
for repeat_count, long_read in zip(repeat_counts, long_reads):
    plt.vlines(repeat_count, ymin=0, ymax=long_read, colors='r')

plt.xlabel('Estimated repeat count', fontsize=14)
plt.ylabel('Number of long reads', fontsize=14)
plt.title('Sample ID: A0000837', fontsize=16)
plt.xlim(0, 400)
plt.ylim(0, 12)
plt.grid(False)
plt.show()
