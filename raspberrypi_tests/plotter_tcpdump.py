import numpy
import Gnuplot
import re
import subprocess
import numpy
from glob import glob
from os import path
from io import TextIOWrapper
from pcappy import open_offline

#throughput_re = re.compile(r"^\s*\"(\d+\.\d+)\",\"(\d+)\"\s*$")
throughput_csv_re = re.compile(r"^(\d+\.\d+),(\d+)\s*$")
throughput_re = re.compile(r"^\s+(\d+\.\d+)\s+(\d+\.\d+)\s+$")


def parse_pcap(file):
	#print(file)
	p = open_offline(file)
	first_packet = p.next()
	
	ts = int(first_packet[0]['ts']['tv_sec'])
	#return ts
	#print(ts)
	
	cmd = ['captcp', 'throughput', '-p', '-r', '-ubit', '-t', file]
	result = subprocess.Popen(cmd, stdout=subprocess.PIPE)
		
	data = []
	for line in result.stdout:
		#print(line)
		if throughput_re.match(line):
			matches = throughput_re.findall(line)[0]
			#print("- " + matches[0] + " - bw: " + matches[1] + " bps")
			data.append((ts+int(float(matches[0])), int(float(matches[1]))))
			
	return data


def get_ts(file):
	p = open_offline(file)
	first_packet = p.next()
	ts = int(first_packet[0]['ts']['tv_sec'])
	return ts


def parse_csv(file, ts):
	f = open(file, 'r')
	data = []
	for line in f.readlines():
		if throughput_csv_re.match(line):
			matches = throughput_csv_re.findall(line)[0]			
			data.append((ts+float(matches[0]), int(float(matches[1]))))
			
			
	#lst = [elemt[1] for elemt in data]
	#print("!!!! " + str(numpy.percentile(lst, 75)))
	#print("!!!! " + str(numpy.percentile(lst, 90)))
	#print("!!!! " + str(numpy.percentile(lst, 95)))
	#print("!!!! " + str(numpy.percentile(lst, 99)))
	
	return data


def overlap(*d):
	lower_bound = 0	
	upper_bound = d[0][-1][0]
	i = 0
	for dataset in d:
		#print(i)
		i += 1
		#print(len(dataset))
		if dataset[0][0] > lower_bound:
			if upper_bound < dataset[0][0]:
				exit(-1)
			lower_bound = dataset[0][0]
		if dataset[-1][0] < upper_bound:
			if lower_bound > dataset[-1][0]:
				print(dataset)
				exit(-1)
			upper_bound = dataset[-1][0]

	print(lower_bound)
	print(upper_bound)

	for dataset in d:
		while True:
			if dataset[0][0] < lower_bound:
				dataset.pop(0)
			elif dataset[-1][0] > upper_bound:
				dataset.pop(-1)
			else:
				break

def trim(start, end, *d):
	for dataset in d:
		del dataset[:start]
		del dataset[-end:]

def trim_to(start, length, *d):
	for dataset in d:
		del dataset[:start]
		del dataset[length:]

def pad(*d):
	lower_bound = d[0][-1][0]
	upper_bound = 0
	for dataset in d:
		if dataset[0][0] < lower_bound:
			lower_bound = dataset[0][0]
		if dataset[-1][0] > upper_bound:
			upper_bound = dataset[-1][0]


	for dataset in d:
		while True:
			if dataset[0][0] > lower_bound:
				dataset.insert(0,(dataset[0][0]-1, 0))
			elif dataset[-1][0] < upper_bound:
				dataset.append((dataset[-1][0]+1, 0))
			else:
				break


def main():

	### CONFIGURATION #####
	folder = "./3/"
	interesting_files = "*.pcap"
	line_data_file = folder+"lines.dat"
	bar_data_file = folder+"bars.dat"
	line_plot_file = folder+"lines.gpi"
	bars_plot_file = folder+"bars.gpi"
	#######################

	files = glob(folder+interesting_files)
	data_sets = []

	#data_sets.append(parse_csv(folder+"pi3-desktop.csv", parse_pcap(folder+"pi3-desktop.pcap")))
	#data_sets.append(parse_csv(folder+"pi2-desktop.csv", parse_pcap(folder+"pi2-desktop.pcap")))
	
	data_sets.append(parse_csv(folder+"pi3-desktop.csv", get_ts(folder+"pi3-desktop.pcap")))

	
	#data_sets.append(parse_csv(folder+"c2.csv", parse_pcap(folder+"c2.pcap")))
	#data_sets.append(parse_csv(folder+"c3.csv", parse_pcap(folder+"c3.pcap")))
	#data_sets.append(parse_csv(folder+"sv1.csv", parse_pcap("/tmp/eval/sv1.pcap")))
	#data_sets.append(parse_csv(folder+"sv2.csv", parse_pcap("/tmp/eval/sv2.pcap")))
	#data_sets.append(parse_csv(folder+"sv3.csv", parse_pcap("/tmp/eval/sv2.pcap")))

	#data_sets = [d for d in data_sets if len(d) >= 500]

	print("Got " + str(len(data_sets)) + " data sets")
	
	overlap(*data_sets)
	#trim(60, 60, *data_sets)
	#trim_to(60, 500, *data_sets)
	#trim(0, 650, *data_sets)
	#pad(*data_sets)

	lines_file = open(line_data_file, mode="w")
	bars_file = open(bar_data_file, mode="w")

	numpy_arrays = []
	total = None
	for i, data in enumerate(data_sets):
		name = "Client"+str(i+1)
		c = numpy.array([int(x[1]) for x in data])
		if total is None:
			total = c.copy()
		else:
			total += c
		numpy_arrays.append(c)
		print(name)
		print(" mean:     " + str(c.mean()))
		print(" max:      " + str(c.max()))
		print(" min:      " + str(c.min()))
		print(" dev:      " + str(c.std()))

	numpy_arrays.append(total)
	print("Total")
	print(" mean:     " + str(total.mean()))
	print(" max:      " + str(total.max()))
	print(" min:      " + str(total.min()))
	print(" total tx: " + str(total.sum()))
	print(" dev:      " + str(total.std()))

	for i in range(len(numpy_arrays[0])):
		line = str(i)
		for j in range(len(numpy_arrays)):
			line += "     " + str(numpy_arrays[j][i])
		lines_file.write(line + "\n")
	lines_file.close()

	for i in range(len(numpy_arrays)):
		if i < len(numpy_arrays)-1:
			name = "Client" + str(i+1)
		else:
			name = "Total"
		bars_file.write(name + "     " +
						str(numpy_arrays[i].mean()) + "     " +
						str(numpy_arrays[i].max()) +  "     " +
						str(numpy_arrays[i].min()) +  "     " +
						str(numpy_arrays[i].std()) +  "\n")

	bars_file.close()

	lplot_file = open(line_plot_file, mode="w")
	plot_lines = []
	plot_lines.append('set xlabel "Seconds"')
	plot_lines.append('set ylabel "Throughput"')
	plot_lines.append('set ytics 10000000')
	plot_lines.append('set mytics 10')
	plot_lines.append('set format y "%.0s%cbit/s"')
	plot_lines.append('set xtics 25')
	plot_line = 'plot'
	for i in range(1, len(numpy_arrays)):
		plot_line += ' "' + path.basename(line_data_file) + '" using 1:' + str(i+1) + " title 'Client" + str(i) + "' with lines,"
	plot_line += ' "' + path.basename(line_data_file) + '" using 1:' + str(len(numpy_arrays)+1) + " title 'Total' with lines"

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
