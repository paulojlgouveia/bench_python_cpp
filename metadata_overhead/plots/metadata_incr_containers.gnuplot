
set term postscript monochrome eps enhanced 22
set output 'metadata_incr_containers.eps'
load "styles.inc"
set size 1,0.6 
set tmargin 0.60

set xlabel ""
set yrange [0:6000]
set ylabel "Bandwidth (Bytes/s)"
set grid y

set style data boxes
set boxwidth 0.9
set style fill solid 1.00

set ytics 0,2000,6000
set mytics 5
set format y "%.0s"
#set format y "%.0s%cbit/s"
set noxtics
set nokey

set label '1F/2C' at 0.80, 25000 font "Helvetica, 22" rotate by 70 front
set label '1F/4C' at 1.80, 25000 font "Helvetica, 22" rotate by 70 front
set label '1F/8C' at 2.80, 25000 font "Helvetica, 22" rotate by 70 front
set label '2F/16C' at 3.80, 25000 font "Helvetica, 22" rotate by 70 front

plot "gnuplotdata/increasing_containers.dat" title "" fill noborder solid 0.5 lc rgb "#DAA520"

!epstopdf "metadata_incr_containers.eps"
!rm "metadata_incr_containers.eps"
