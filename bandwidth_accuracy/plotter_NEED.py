import numpy
import Gnuplot
from glob import glob
from os import path
import json
import sys

#time unit, default is 1.0
UNIT=1.0

def parse_NEED_log(file):
	f = open(file)
	data_sets = {}
	accumulated = []

	lines = f.readlines()# [1:-1]

	for line in lines:
		output = json.loads(line)
		for key in output:
			if key == 'ts':
				continue
			if output[key][0] < 1000:
				# ignore below 1Mbps threshold (if we ignore a valid flow an error will be thrown later)
				continue
			sender_id = key.split(':')[0]
			if sender_id in data_sets:
				data_sets[sender_id].append((output['ts'], output[key][0]))
			else:
				data_sets[sender_id] = [(output['ts'], output[key][0])]
			accumulated.append(output[key][1])

	print("----------------------------------")
	n = numpy.array(accumulated)
	print("Average: " + str(n.mean()))
	print("Median:  " + str(numpy.median(n)))
	print("Min:     " + str(n.min()))
	print("Max:     " + str(n.max()))
	print("Avg Gap: " + str(1000/n.mean()) + "ms")
	counts = dict(zip(*numpy.unique(n, return_counts=True)))
	# for i in counts:
	#     print(str(i) + ":" + str(counts[i]))
	print("----------------------------------")
	
	
	returnval = [data_sets[k] for k in data_sets]
	return returnval

def overlap(*d):
	lower_bound = 0
	upper_bound = d[0][-1][0]
	
	#
	print("!!! d[0][-1] " + str(d[0][-1]))
	# print("!!! d[0] " + str(d[0]))
	# print("!!! d[1] " + str(d[1]))
	
	
	
	max_len = 0
	for dataset in d:
		if len(dataset) > max_len:
			max_len = len(dataset)
	
	
	#min_len = max_len/2
	#to_delete = []
	#i = 0
	#for dataset in d:
		#if len(dataset) < min_len:
			#to_delete.append(i)
		#i += 1
	
	#for idx in to_delete:
		#d.pop(idx)
	
	
	
	min_len = max_len/2
	new_data = []
	for dataset in d:
		if len(dataset) > min_len:
			new_data.append(dataset)

	
	
	i = 0
	for dataset in new_data:
		print(str(i) + " - " + str(len(dataset)))
		i += 1
		if dataset[0][0] > lower_bound:
			if upper_bound < dataset[0][0]:
				print("!!! " + str(upper_bound) + " < " + str(dataset[0][0]) + "\n" + str(dataset))
				exit(-1)
			lower_bound = dataset[0][0]
		if dataset[-1][0] < upper_bound:
			if lower_bound > dataset[-1][0]:
				print("!!! " + str(lower_bound) + " > " + str(dataset[-1][0]) + "\n" + str(dataset))
				exit(-1)
			upper_bound = dataset[-1][0]

	print("lower_bound " + str(lower_bound))
	print("upper_bound " + str(upper_bound))
	
	for dataset in new_data:
		while True:
			if dataset[0][0] < lower_bound:
				dataset.pop(0)
			elif dataset[-1][0] > upper_bound:
				dataset.pop(-1)
			else:
				break
			
			
	return new_data


def trim(start, end, *d):
	for dataset in d:
		del dataset[:start]
		del dataset[-end:]

def trim_to(start, length, *d):
	for dataset in d:
		del dataset[:start]
		del dataset[length:]

def pad(*d):

	lower_bound = float('inf')
	upper_bound = 0
	for dataset in d:
		if dataset[0][0] < lower_bound:
			lower_bound = dataset[0][0]
		if dataset[-1][0] > upper_bound:
			upper_bound = dataset[-1][0]
	
	print("Padding from " + str(lower_bound) + " to " + str(upper_bound))
	print("Totals " + str(int(upper_bound-lower_bound)) + " seconds")


	for dataset in d:
		print("padding " + str(dataset[0][0]) + " " + str(dataset[-1][0]))
		
		#extend start and end
		while True:
			if dataset[0][0] > lower_bound+0.5*UNIT:
				print("padding start at " + str(dataset[0][0]))
				dataset.insert(0,(dataset[0][0]-UNIT, 0))
				print("inserting at " + str(dataset[0][0]))
			elif dataset[-1][0] < upper_bound-0.5*UNIT:
				print("padding end at " + str(dataset[-1][0]))
				dataset.append((dataset[-1][0]+UNIT, 0))
				print("inserting at " + str(dataset[-1][0]))
			else:
				break
		
		#fill gaps in middle
		print('fill gaps in middle')
		last = dataset[0][0]
		i = 1
		end = len(dataset)
		while True:
			#print("iterating at " + str(dataset[i][0]))
			if dataset[i][0] >= last+1.5*UNIT:
				dataset.insert(i, (last+UNIT, 0))
				#print("inserting at " + str(dataset[i][0]))
				i -= 1
			last = dataset[i][0]
			i += 1
			if i == end:
				break

		print("result " + str(dataset[0][0]) + " " + str(dataset[-1][0]))
		print(len(dataset))

def main():

	### CONFIGURATION #####
	folder = "./"
	folder = "./" + sys.argv[1]
	interesting_files = "*.json"
	line_data_file = folder+"lines.dat"
	bar_data_file = folder+"bars.dat"
	totals_data_file = folder+"totals.dat"
	line_plot_file = folder+"lines.gpi"
	bars_plot_file = folder+"bars.gpi"
	#######################

	files = glob(folder+interesting_files)
	data_sets = []

	for file in files:
		data_sets = parse_NEED_log(file)
	#return

	#data_sets = [d for d in data_sets if len(d) >= 600]

	print("Got " + str(len(data_sets)) + " data sets")

	data_sets = overlap(*data_sets)
	# trim(60, 60, *data_sets)
	trim_to(60, 480, *data_sets)
	#trim(0, 650, *data_sets)
	#pad(*data_sets)

	lines_file = open(line_data_file, mode="w")
	bars_file = open(bar_data_file, mode="w")
	totals_file = open(totals_data_file, mode="w")

	numpy_arrays = []
	total = None
	for i, data in enumerate(data_sets):
		name = "Client"+str(i+1)
		c = numpy.array([int(x[1])*1000 for x in data])
		#if total is None:
		#    total = c.copy()
		#else:
		#    total += c
		numpy_arrays.append(c)
		print(name)
		print(" mean:     " + str(c.mean()))
		print(" max:      " + str(c.max()))
		print(" min:      " + str(c.min()))
		print(" dev:      " + str(c.std()))

	#numpy_arrays.append(total)
	#print("Total")
	#print(" mean:     " + str(total.mean()))
	#print(" max:      " + str(total.max()))
	#print(" min:      " + str(total.min()))
	#print(" total tx: " + str(total.sum()))
	#print(" dev:      " + str(total.std()))
	
	totals = numpy.array([x for x in c for c in numpy_arrays])

	for i in range(len(numpy_arrays[0])):
		line = str(i*UNIT)
		for j in range(len(numpy_arrays)):
			line += "     " + str(numpy_arrays[j][i])
		lines_file.write(line + "\n")
	lines_file.close()
	
	totals_file.write("#id     25th     50th     75th     90th     95th     99th     100th\n")
	totals_file.write("Overall" + "     " +
					str(numpy.percentile(totals, 25)) +  "     " +
					str(numpy.percentile(totals, 50)) +  "     " +
					str(numpy.percentile(totals, 75)) +  "     " +
					str(numpy.percentile(totals, 90)) +  "     " +
					str(numpy.percentile(totals, 95)) +  "     " +
					str(numpy.percentile(totals, 99)) +  "     " +
					str(numpy.percentile(totals, 100)) +  "\n")
	totals_file.close() 

	bars_file.write("#id     mean     max     min     std     50th     95th     25th     50th     75th     90th     95th     99th     100th\n")
	for i in range(len(numpy_arrays)):
		#if i < len(numpy_arrays)-1:
		name = "Client" + str(i+1)
		#else:
		#    name = "Total"
		bars_file.write(name + "     " +
						str(numpy_arrays[i].mean()) + "     " +
						str(numpy_arrays[i].max()) +  "     " +
						str(numpy_arrays[i].min()) +  "     " +
						str(numpy_arrays[i].std()) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 50)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 95)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 25)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 50)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 75)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 90)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 95)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 99)) +  "     " +
						str(numpy.percentile(numpy_arrays[i], 100)) +  "\n")

	bars_file.close()

	lplot_file = open(line_plot_file, mode="w")
	plot_lines = []
	plot_lines.append('set xlabel "Seconds"')
	plot_lines.append('set ylabel "Throughput"')
	plot_lines.append('set ytics 10000000')
	plot_lines.append('set mytics 10')
	plot_lines.append('set format y "%.0s%cbit/s"')
	plot_lines.append('set xtics 5')
	plot_lines.append('set mxtics 5')
	plot_line = 'plot'
	for i in range(1, len(numpy_arrays)):
		plot_line += ' "' + path.basename(line_data_file) + '" using 1:' + str(i+1) + " title 'Client" + str(i) + "' with lines,"
	plot_line += ' "' + path.basename(line_data_file) + '" using 1:' + str(len(numpy_arrays)+1) + " title 'Client" + str(len(numpy_arrays)) + "' with lines"

	plot_lines.append(plot_line)
	lplot_file.writelines([l+"\n" for l in plot_lines])
	lplot_file.close()

	bplot_file = open(bars_plot_file, mode="w")
	plot_lines = []
	plot_lines.append('set ylabel "Throughput"')
	plot_lines.append('set ytics 10000000')
	plot_lines.append('set mytics 10')
	plot_lines.append('set format y "%.0s%cbit/s"')
	plot_lines.append('set boxwidth 0.7')
	plot_lines.append('set style fill solid 0.5')
	plot_lines.append('plot "' + path.basename(bar_data_file) + '" using 2:xtic(1) with boxes lc rgb "#DAA520" title "Mean throughput", \\')
	plot_lines.append('""        using 0:2:3:4 with yerrorbars lt 1 lc rgb "#AA0000" title "Min-Max", \\')
	plot_lines.append('""         using 0:2:5 with yerrorbars lt 1 lc rgb "#00AA00" title "Standard deviation"')
	bplot_file.writelines([l+"\n" for l in plot_lines])
	bplot_file.close()

if __name__ == '__main__':
	main()
