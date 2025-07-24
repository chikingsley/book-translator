from alive_progress import alive_bar;
import time

for total in 5000, 7000, 4000, 0:
    with alive_bar(total, title='Processing', bar='smooth') as bar:
        for i in range(total):
            time.sleep(0.001) 
            bar()  
    print(f"Completed processing {total} items.\n")

