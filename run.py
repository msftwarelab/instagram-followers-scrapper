import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient
from datetime import datetime

# Date and time
current_time = datetime.now()
result_folder = current_time.strftime("result_%Y_%m_%d")

# MongoDB configuration
mongo_url = ""

try:
    with open("mongodb.txt", 'r') as file:
        lines = file.readlines()
        mongo_url = lines[0]
except:
    mongo_url = input("Enter a mongodb url: ")

    with open("mongodb.txt", 'w') as file:
        file.write(f"{mongo_url}\n")

client = MongoClient(mongo_url)
db = client.get_database("heatmapper")

collection = db.get_collection("targets")
cursor = collection.find()

users_to_parse = [{"name": "coldaf_ethan", "category": "test"}]

# for document in cursor:
#     users_to_parse.append({"name": document["name"], "category": document["category"]})


# Credentials configuration
credss = []
folder_path = "accounts"

if os.path.exists(folder_path) and os.path.isdir(folder_path):
    file_list = os.listdir(folder_path)
    
    for file_name in file_list:
        if file_name.endswith(".txt"):
            file_path = os.path.join(folder_path, file_name)
            
            with open(file_path, "r") as file:
                creds = file.readlines()
                credss.append(creds)
else:
    print("The accounts directory does not exist or is not a directory.")
    sys.exit()

index_target = -1
index = -1
result = []

# Scrap engine
for item in users_to_parse:
    user = item["name"]
    category = item["category"]

    index_target = index_target + 1
    index = index + 1
    if index >= len(credss):
        index = 0

    creds = credss[index]
    
    chrome_options = Options()

    # chrome_options.add_argument("--headless")  # To check in CLI, comment out this line
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = ChromeService(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Open the webpage
    driver.get("http://www.instagram.com")

    # Target username
    username = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']")))

    # Target Password
    password = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='password']")))

    # Enter username and password
    username.clear()
    username.send_keys(creds[0])
    password.clear()
    password.send_keys(creds[1])

    # Target the login button and click it
    button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()


    time.sleep(5)

    print(f"###### {creds[0]}")

    try:
        print(f"Scraping {user}")

        driver.get(f"https://www.instagram.com/{user}/following/")

        time.sleep(7)

        # Scroll till following list is there
        fBody = driver.find_element(By.XPATH, "//div[@class='_aano']")

        users = []
        global_elements = []

        which_try = 0

        while True:
            try:
                elements = driver.find_elements(By.XPATH, "//span[contains(@class, '_aacl')]")
                if global_elements == elements:
                    if which_try < 20:
                        which_try += 1
                    else:
                        break

                else:
                    which_try = 0

                for i in elements:
                    if i.text not in users:
                        print(f"|--> {index_target + 1}:{len(users) + 1}: {i.text}")
                        users.append(i.text)

                global_elements = elements

                driver.execute_script('arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight;', fBody)

                elements = driver.find_elements(By.XPATH, "//span[contains(@class, '_aacl')]")

                for i in elements:
                    if i.text not in users:
                        print(f"|--> {index_target + 1}:{len(users) + 1}: {i.text}")
                        users.append(i.text)

                global_elements = elements

                driver.execute_script('arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight;', fBody)

                if which_try > 3:
                    time.sleep(1.5)
            except Exception as e:
                print(e)
                continue

        print(f"Followings: {len(users)}")
        print(f"Finished {user}\n")
        
        if not os.path.exists(f"results/{result_folder}"):
            os.makedirs(f"results/{result_folder}")

        with open(f"results/{result_folder}/{user}.txt", 'w') as file:
            for i in users:
                file.write(f"{i}\n")

        result.append({"target": user, "category": category, "following": users})

    except Exception as e:
        print(e)
        continue

    driver.quit()


# Store scrapping result
print("######################################")
print("Sumarize the result")

collection = db.get_collection("instagrams")
document = {
    "date": current_time,
    "data": result
}
collection.insert_one(document)


# Summarize the result
print("######################################")
print("Sumarize the result")

finalResult = {}

for item in result:
    target = item["target"]
    category = item["category"]
    accounts = item["following"]

    for account in accounts:
        if account in finalResult:
            finalResult[account]["significance"] = finalResult[account]["significance"] + 1
            finalResult[account]["growth"][len(finalResult[account]["growth"]) - 1] = finalResult[account]["growth"][len(finalResult[account]["growth"]) - 1] + 1
            finalResult[account]["fellowBy"].append(target)

        else:
            finalResult[account] = {"name": account, "category": category, "significance": 1, "growth": [1], "fellowBy": [target], "deleted": 0}


# Store final result
print("######################################")
print("Store final result in database")

collection = db.get_collection("accounts")

for key in finalResult:
    account = finalResult[key]

    query = {"name": account["name"]}
    document = collection.find_one(query)
    if document:
        document["growth"].append(account["significance"])
        updateQuery = {"_id": document["_id"]}
        update_operation = {
            "$set": {
                "category": account["category"],
                "significance": account["significance"],
                "growth": document["growth"],
                "fellowBy": account["fellowBy"]
            }
        }
        collection.update_one(updateQuery, update_operation)
    else:
        collection.insert_one(account)

    print(f"|--> {account['name']}")


client.close()
