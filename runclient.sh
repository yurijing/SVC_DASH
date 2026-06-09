i=1
while [ "$i" -le "40" ]
do
	sum=$(($sum + $i))
	i=$(($i+1))
	sudo python3 Client.py 
        sudo rm -rf *.svc
	
done
