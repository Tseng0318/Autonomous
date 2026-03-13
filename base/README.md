** steps to the file and how to run
open teminal
cd Desktop
cd ENEL500
source enel500/bin/activate
cd Automation
cd preset_path
** now you are in the folder where the main files are
eg python3 new_main.py


The logic works as following:
(RUN THE new_main.py file, this is the top level loop)

1 Lidar scan
2 rover approach and stop
3 first rotation random: rover perform a random 90 degree rotation
4 rover move foward a little bit
5 second rotation: rover perform the same direction rotation as the first
eg. if the first time the rover turned right,the second time would also turn right
6 Start the loop again

DEMO Video: https://drive.google.com/file/d/1objeHKCd6fR-jWB1OGfOA8x9HnwabTlW/view?usp=sharing


The base detection is done but not yet incorporated in the rover movement
