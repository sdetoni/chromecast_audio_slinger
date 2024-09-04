export PATH=$(pwd)/python-slinger/bin:$PATH
export url=$(ip a  | grep inet | grep global | awk -F'/' '{print $1}' | awk '{print "http://"$2":8008"}')
echo Access Program from $url
python3 runner.py &

