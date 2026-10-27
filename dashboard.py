from tkinter import *
import random

root = Tk()
root.title("Plastic Factory Simulator")
root.geometry("600x400")

produced = 0
defective = 0

count_label = Label(root, text="Produced Bottles : 0",
                    font=("Arial", 16))
count_label.pack(pady=10)

defect_label = Label(root, text="Defective Bottles : 0",
                     font=("Arial", 16))
defect_label.pack(pady=10)

temp_label = Label(root, text="Temperature : 35°C",
                   font=("Arial", 16))
temp_label.pack(pady=10)

status_label = Label(root, text="Machine Status : RUNNING",
                     font=("Arial", 16))
status_label.pack(pady=10)

def auto_produce():
    global produced, defective

    produced += 1

    if random.randint(1, 10) == 1:
        defective += 1

    temperature = random.randint(35, 50)

    count_label.config(
        text=f"Produced Bottles : {produced}"
    )

    defect_label.config(
        text=f"Defective Bottles : {defective}"
    )

    temp_label.config(
        text=f"Temperature : {temperature}°C"
    )

    root.after(1000, auto_produce)

auto_produce()

root.mainloop()
