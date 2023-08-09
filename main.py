from subprocess import Popen, PIPE
from multiprocessing import Pool, freeze_support
from datetime import datetime
import time
from IPScraper import scan, ip_results
import os
import sys
import shutil
import json


def main():

     # Get the inital time and date for the start of the program
     now = datetime.now()
     dt_string = now.strftime("%m_%d_%Yat%I_%M_%S%p")
     dt_print = now.strftime("%m/%d/%Y at %I:%M:%S%p")


     # ERROR-HANDLING with pyinstaller executable, determines if application is a script file or frozen exe
     if getattr(sys, 'frozen', False):
          application_path = os.path.dirname(sys.executable)
     elif __file__:
          application_path = os.path.dirname(__file__)

     #config file name
     config_name = 'config.txt'

     # Path for config file (which stores the path for the output folder and more...)
     config_path = os.path.join(application_path, config_name)  

     # Start working on using .json file as configuration file
     #config = load_config(config_path)


     # Reading the config file for the path to the output folder and storing to variable
     config_file = open(config_path,"r+")
     output_path_from_config = config_file.read()    

     # temp directory path (this directory will hold ping test results for each device tested in separate files)
     temp_path = os.path.join(application_path, "temp")

     # Deleting all contents of temp directory  
     for item in os.listdir(temp_path):
               item_path = os.path.join(temp_path, item)
               if os.path.isfile(item_path):  # Check if it's a file
                    os.remove(item_path)  # Remove the file
               elif os.path.isdir(item_path):  # Check if it's a directory
                    shutil.rmtree(item_path)  # Remove the directory and its contents

     # Saving the path for output, summary, and event file
     output_data_file = output_path_from_config + "\\"
     output_summary_file = output_data_file
     output_event_file = output_data_file

     # Printing output file directory, and allowing user to change destination directory
     # If changed, the output directory is saved by modifying the config file
     print("The output files directory is set to \n\n" + output_data_file + "\n")
     output_path = input("Press enter to ignore, or type in the complete directory: ")
     print(output_path)
     if (output_path != ""):
          output_path_from_config = output_path
          with open(config_path, "w") as file:
               file.write(output_path_from_config)
          output_data_file = output_path_from_config + "\\"
          output_summary_file = output_data_file
          output_event_file = output_data_file
     else:
          output_data_file = output_data_file
          output_summary_file = output_data_file
          output_event_file = output_data_file
          
     # Creates the full file name for the output, summary, and event output files
     output_data_file += dt_string + ".txt"
     output_summary_file += dt_string + "_Summary.txt"
     output_event_file += dt_string + "_Event_Log.txt"

     # User inputs testing time length
     hours = 8
     print("How many hours would you like to test for?")
     test_hours = float(input("Type in the correct hours: "))
     if (test_hours != ""):
          hours = test_hours
     print(hours)

     # Scans network for controllers (allows for 192.168.0.x and 192.168.1.x)
     print("Scanning network for devices")
     ip_addr = "192.168.1.1/23"
     scanned_output = scan(ip_addr)

     # Date and time of when Ping Testing Begins
     now = datetime.now()
     dt_print = now.strftime("%m/%d/%Y at %I:%M:%S %p")
     start_time = now.strftime("%I:%M:%S %p")

     # Prints the list of IP addresses and MAC addresses of devices being tested
     print("Testing the following IP Addresses " + dt_print + "\n")  
     ip_addresses = ip_results(scanned_output)
     print("Number of Devices:",len(ip_addresses))
     devices = float(len(ip_addresses))

     # Calculating how many packets to send based on number of targets and available thread count
     # to fit in allotted time frame
     seconds = float(3600 * hours)
     threads = 12

     # Calculating the amount of batches to complete the test in
     # Always Rounding Up Segments (Divisions due to limitations on thread count)
     segments = float(devices/threads)
     if segments != float(int(devices/threads)):
          segments = int(segments)
          segments += 1
     else:
          segments = int(segments)

     if int(segments) == 0:
          packets = int(seconds/1)
     else:
          packets = int(seconds/float(segments))

     # Creates a nested list with the IP address of each device and the number of packets to send
     ip_packet = []
     for i in ip_addresses:
          ip_packet.append([i,packets])

     # execute ping test on all ip addresses simultaneously (limited by thread count) (starmap allows for multiple arguments to be passed)
     with Pool() as pool:
          pool.starmap(ping, ip_packet)

     # date and time of end of ping test
     now = datetime.now()
     dt_print = now.strftime("%m/%d/%Y at %I:%M:%S %p")
     end_time = now.strftime("%I:%M:%S %p")
     print("\nPing Test On All IP Addresses Completed " + dt_print + "\n")

     # Summary File Header
     with open(output_summary_file, "a") as file:
          file.write("Summary Results\n\n" + str(hours) + " Hour Test\n\nSTART TIME: " + start_time + "\n\n")

     # Event Log Header
     with open(output_event_file, "a") as file:
          file.write("Event Log \n\n" + str(hours) + " Hour Test\n\nSTART TIME: " + start_time + "\n\n")

     # Counter for devices that passed
     devices_passed = 0

     # Combines the individual files into one large file, and analyzing data to construct the summary and event files
     for each_file in os.listdir(temp_path):

          # Opening each file as read and appending it to main data file
          each_file = os.path.join(temp_path, each_file)
          with open(each_file, "r") as source_file, open(output_data_file, "a") as destination_file:
                    output = source_file.read()
                    destination_file.write(output)
               
          # Searching for IP Address within the text file
          ip_start = output.find("Pinging ")
          ip_end = output.find(" with 32 bytes of data")
          ip = output[ip_start + 8: ip_end]

          # Checks for indicator of PASS OR FAIL (FAIL is when at least one packet is lost)
          pass_or_fail = output.find("RESULT IS FAIL")
          if pass_or_fail == -1:
               test = "PASS"
               devices_passed += 1
          else:
               test = "FAIL"

          # Searches for value that provides percentage packet loss within text file
          test_start = output.find("(")
          test_end = output.find("%")
          loss = output[test_start + 1: test_end + 6]

          # checks if it was ever disconnected, and changes message to FAIL (WAS DISCONNECTED) if it was
          unreachable = output.find("DISCONNECTED")
          if unreachable != -1:
               test += " (WAS DISCONNECTED)"
               loss = "N/A"

          # Finding Event Log
          event_start = output.find("EVENT LOG")
          event_end = output.find("END LOG")
          event = output[event_start: event_end]

          # Writing to Summary File
          with open(output_summary_file, "a") as file:
               file.write(ip + "\t\t" + loss + "\t\t" + test + "\n")

          # Writing to Event Log
          with open(output_event_file, "a") as file:
               file.write(ip + "\n" + event + "\n")
          


     # Writes the number of devices that passed into summary file
     with open(output_summary_file, "a") as file:
          file.write("\n" + str(devices_passed) + " out of " + str(int(devices)) + " devices PASSED\n\nEND TIME: " + end_time + "\n\n")

     # Writes the end time into event log
     with open(output_event_file, "a") as file:
          file.write("END TIME: " + end_time)

     # End date and time
     now = datetime.now()
     dt_print = now.strftime("%m/%d/%Y at %I:%M:%S %p")
     
     print("Finished " + dt_print + "\n")
     input()


def load_config(config_path):
     with open(config_path, "r") as file:
          config_data = json.load(file)
     return config_data

def save_config(config_path, config_data):
     with open(config_path, "w") as file:
          json.dump(config_data, file, indent=4)

# Performs Ping Test on each IP Address
def ping (host, packets):
     
     # ERROR-HANDLING with pyinstaller executable, determines if application is a script file or frozen exe
     # Finds application path to be used to find temp directory
     if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
     elif __file__:
        application_path = os.path.dirname(__file__)
     temp_path = os.path.join(application_path, "temp")

     # Name of text file for each device (named ipaddress.txt)
     temp_file_name = temp_path + "\\" + host + ".txt"


     # Open the text file and writes the data as it is output from Popen
     with open(temp_file_name, "a") as file:   
          
          # Result of 1 means the device PASSED
          result = 1
          
          output = " "
          
          # Open ping function and pings IP with n packets
          output= Popen(f"ping {host} -n {packets}", stdout=PIPE, encoding="utf-8")
          
          # Initial state of device is ONLINE
          state_before = "ONLINE"
          time_elapsed = "EVENT LOG:\n"

          # Records start time and date of test for each device
          start_time = time.time()
          end_time = 0
          now = datetime.now()
          dt_print = now.strftime("%m/%d/%Y at %H:%M:%S PST ")

          # If this counter reaches 5, it means the device was disconnected and the ping test terminates
          terminate_counter = 0

          # This goes through each line of data from Popen as it occurs
          for line in output.stdout:
               
               file.write(line)

               # If Request Timed Out, result = 0 means FAIL and switched to OFFLINE state
               if line[0:3] == "Req":
                    state_after = "OFFLINE"
                    result = 0
               # If unreachable, then DISCONNECTED and terminate counter increases
               elif line.find("unreachable") != -1:
                    state_after = "DISCONNECTED"
                    terminate_counter += 1
               else:
                    state_after = "ONLINE"
               
               # If the state changes, it calculates the time that passed between the states in seconds and records time and datestamp
               if state_before != state_after:
                    end_time = time.time()
                    now = datetime.now()
                    dt_print = now.strftime("%m/%d/%Y at %H:%M:%S PST ")
                    time_difference = end_time - start_time
                    time_elapsed += dt_print + state_before + " for " + str(round(time_difference, 3)) + " s\n"
                    start_time = end_time

               # Updates the previous state for loop
               state_before = state_after

               # Cancel Ping Test on this device to save time
               if terminate_counter >= 5:
                    output.terminate()


          # At end of test, calculate time for most recent state
          end_time = time.time()
          time_difference = end_time - start_time
          time_elapsed += dt_print + state_before + " for " + str(round(time_difference, 3)) + " s\nEND LOG"
          
          # If state never changes, error-handling
          if end_time == 0:
               end_time = time.time()
               time_difference = end_time - start_time
               time_elapsed += state_before + " for " + str(round(time_difference, 3)) + " s\nEND LOG"

          # If result changed from 1 to 0
          if result == 0:
               file.write("RESULT IS FAIL\n")

          # Write final lines of data
          file.write(time_elapsed)

     # Close the Popen process
     output.stdout.close()

if __name__ == "__main__":
    # Due to Multiprocessing module
    freeze_support()
    main()
    