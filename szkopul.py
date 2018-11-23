#!/usr/bin/python3
# -*- coding: utf-8 -*-

# if __name__ == "__main__":
# 	username = "username"
# 	password = "password"
# 	contest_name = "contest_name"
# 	round_id = "round_id"

# if __name__ == "__main__":
# 	username = "czeslaw"
# 	password = ""
# 	contest_name = "25-oi-przygotowania"
# 	round_id = "3589"

if __name__ == "__main__":
	with open("user.txt", "r") as user_file:
		username = user_file.readline().strip()
		password = user_file.readline().strip()
		contest_name = user_file.readline().strip()
		round_id = user_file.readline().strip()

from bs4 import BeautifulSoup
from bs4 import NavigableString
import requests
import pypandoc
import os
import shutil
import re
import argparse
import subprocess
import sys
import time

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("type", help="typ polecenia (update - zaktualizuj listę zadań, gen - wygeneruj paczkę, search" \
		"- przeszukaj bazę zadań)", type=str, choices=["update", "gen", "search"])
	parser.add_argument("-n", "--name", help="nazwa zadania (do wyszukiwania)", type=str)
	parser.add_argument("-i", "--id", help="index zadania (do wyszukiwania)", type=str)
	parser.add_argument("-l", "--label", help="label zadania (do wyszukiwania)", type=str)
	parser.add_argument("-t", "--tag", help="tagi zadania (do wyszukiwania), kolejne tagi poodzielaj spacjami", type=str)
	parser.add_argument("-e", "--eng", help="ignoruje treści po angielsku", action="store_true")

	parser.add_argument("-c", "--contest", help="nazwa konkursu (do pdf)", type=str, default="")
	parser.add_argument("-d", "--date", help="data konkursu (do pdf)", type=str, default="")
	parser.add_argument("-f", "--footer", help="informacje do stopki (do pdf)", type=str, default="")
	parser.add_argument("-m", "--memory", help="ręczne ustawienie limitu pamięci (w MB)", type=str)

	parser.add_argument("-w", "--input", help="pobierz pliki in", action="store_true")
	parser.add_argument("-o", "--output", help="pobierz pliki out", action="store_true")
	parser.add_argument("-g", "--generate", help="wygeneruj outy przez rozwiązanie", action="store_true")
	parser.add_argument("-p", "--pdf", help="stwórz plik pdf", action="store_true")
	parser.add_argument("-s", "--solutions", help="pobierz rozwiązania", action="store_true")
	parser.add_argument("-k", "--config", help="stwórz plik konfiguracyjny", action="store_true")
	parser.add_argument("-r", "--limits", help="dodaj limity czasu do pliku konfiguracyjnego", action="store_true")
	parser.add_argument("-z", "--zip", help="spakuj paczkę do zipa", action="store_true")

	parser.add_argument("-v", "--verbose", help="wyświetl dodatkowe informacje na wyjściu", action="store_true")
	parser.add_argument("-q", "--quiet", help="nic nie wyświetla na wyjściu", action="store_true")
	argv = parser.parse_args()

class Paczkarka:
	# private

	def __myPrint(self, *args, indent=0, **kwargs):
		if self.quiet == False:
			print("  " * indent, end="", file=sys.stderr)
			print(*args, file=sys.stderr, **kwargs)

	def __makeDir(self, f):
		d = os.path.dirname(f)
		if not os.path.exists(d):
			os.makedirs(d)

	# remove unnecessary whitespaces
	def __htmlPreprocess(self, html):
		pat = re.compile("(^[\s]+)|([\s]+$)", re.MULTILINE)
		html = re.sub(pat, "", html)       # remove leading and trailing whitespaces
		html = re.sub("\n", " ", html)     # convert newlines to spaces
		                                   # this preserves newline delimiters
		html = re.sub("[\s]+<", "<", html) # remove whitespaces before opening tags
		html = re.sub(">[\s]+", ">", html) # remove whitespaces after closing tags
		return html

	def __tooFileName(self, text):
		ltrPL = "ŻÓŁĆĘŚĄŹŃżółćęśąźń -()"
		ltrnoPL = "ZOLCESAZNzolcesazn__[]"
		return text.translate(str.maketrans(ltrPL, ltrnoPL))

	# convert given html code to latex
	def __getLatex(self, text):
		dr = "/tmp/paczkarka-tmp-" + str(os.getpid()) + ".html"
		with open(dr, "w") as ss:
			ss.write(text)
		ret = pypandoc.convert_file(dr, "tex")
		return ret

	# repair file name for easier file manipulation
	def __repairFileName(self, text):
		dir_name = os.path.dirname(text)
		if dir_name == "":
			dir_name = "images"
		ret = dir_name + "/" + (os.path.splitext(os.path.basename(text))[0]).replace(".", "-")
		return ret

	# download photo, repair name and convert to png
	def __getPhoto(self, site, init_name): 
		url = site + init_name
		ext = os.path.splitext(os.path.basename(init_name))[1]
		self.__myPrint("Pobieranie obrazka " + init_name + " z " + url, indent=1)

		response = requests.get(url, stream=True)

		rep_name = self.__repairFileName(init_name)
		final_name = rep_name + ".png"
		rep_name += ext

		if rep_name != init_name:
			self.__myPrint("Zmiana nazwy " + init_name + " na " + rep_name, indent=1)

		self.__makeDir(self.latex_dir + rep_name)
		self.__myPrint("Zapisywanie obrazka w " + self.latex_dir + rep_name, indent=1)
		with open(self.latex_dir + rep_name, "wb") as out:
			shutil.copyfileobj(response.raw, out)

		if ext != ".png":
			self.__myPrint("Konwertowanie pliku " + ext + " do .png", indent=1)
			subprocess.call(["convert " + self.latex_dir + rep_name + " " + self.latex_dir + final_name],
			                shell=True, stdout=self.OUT, stderr=self.OUT)
			os.remove(self.latex_dir + rep_name)

		del response
		self.__myPrint("")
		return final_name

	def __compileStatement(self):
		self.__myPrint("Kompilowanie pliku " + self.latex_dir + self.latex_file, indent=1)
		for i in range(2):
			subprocess.call(["cd " + self.latex_dir + " ; pdflatex --interaction nonstopmode " + self.latex_file],
			                shell=True, stdout=self.OUT, stderr=self.OUT)
		self.__makeDir(self.pdf_dir)
		subprocess.call(["cp " + self.latex_dir + self.pdf_file + " " + self.pdf_dir],
		                shell=True, stdout=self.OUT, stderr=self.OUT)

	def __createPdf(self):
		site = self.session.get(self.problem_url + "/site/?key=statement")
		bs = BeautifulSoup(site.text, "html5lib")
		bs = bs.find("div", class_="nav-content")

		if self.info["memoryLimit"] == "":
			try:
				self.info["memoryLimit"] = bs.find("h3").string.split(": ")[1]
			except:
				self.info["memoryLimit"] = "Not found"
		self.info["inter"] = ""

		if bs.h3 == None:
			bs = bs.h1
		else:
			bs = bs.h3

		# check if string does not describe url
		notUrl = lambda href : href and not re.compile("^((http|ftp|https)://)?[^\s/]+\.[^\s]+$").search(href)

		for i in bs.next_siblings:
			if isinstance(i, NavigableString):
				self.info["inter"] += self.__getLatex(str(i))
				continue

			if i.name == "h2":
				i.name = "h1"

			for j in i.findAll(href=notUrl):
				j["href"] = self.problem_url + "/site/" + j["href"]

			if i.name == "img":
				i["src"] = self.__getPhoto(self.problem_url + "/site/", i["src"])
			for j in i.findAll("img"):
				j["src"] = self.__getPhoto(self.problem_url + "/site/", j["src"])

			self.info["inter"] += self.__getLatex(str(i))

		self.info["inter"] = re.sub(r"\"", r"{\\textquotedbl}", self.info["inter"])

		template = ""
		with open("template.tex", "r") as temp:
			template = temp.read()
		latex = template

		matches = [match.span() for match in re.finditer(r"~[^~]*~", template)]

		for match in reversed(matches):
			a = match[0]
			b = match[1]
			var = template[a + 1 : b - 1]
			latex = template[: a] + self.info[var] + latex[b:]

		self.__makeDir(self.latex_dir)
		with open(self.latex_dir + self.latex_file, "w") as file:
			file.write(latex)

		self.__myPrint("Kompilowanie pliku tex do pdf")
		self.__compileStatement()

	# downloads prepared pdf or creates from html
	def __getStatement(self):
		self.__myPrint("Tworzenie treści")
		site = self.session.get(self.problem_url + "/site/?key=statement")
		bs = BeautifulSoup(self.__htmlPreprocess(site.text), "html5lib")
		# there is prepared pdf
		if bs.find(text=re.compile("Możesz otworzyć treść zadania klikając")):
			site = self.session.get(self.problem_url + "/statement", stream=True)
			self.__makeDir(self.pdf_dir)
			with open(self.pdf_dir + self.pdf_file, "wb") as file:
				for chunk in site.iter_content(1024):
					file.write(chunk)
		# no prepared pdf - create from html
		else:
			self.__createPdf()

	def __createArchive(self):
		self.__myPrint("Pakowanie paczki")
		subprocess.call(["zip -r " + self.task_dir + ".zip " + self.task_dir],
		                shell=True, stdout=self.OUT, stderr=self.OUT)

	def __login(self):
		self.__myPrint("Logowanie na szkopuła")
		self.session.get(self.login_url)
		token = self.session.cookies.get_dict()["csrftoken"]
		req = requests.Request("POST", self.login_url,
		                       headers={"Referer" : self.szkopul},
		                       data={"csrfmiddlewaretoken" : token,
		                             "auth-password" : self.password,
		                             "auth-username" : self.username,
		                             "login_view-current_step" : "auth"})
		prepared = self.session.prepare_request(req)
		self.session.send(prepared)
		self.loged = True

	def __addProblem(self, url_key):
		if self.loged == False:
			self.__login()
		self.__myPrint("Dodawanie problemu na szkopuła")
		self.session.get(self.contest_url + "problems/add?key=problemset_source")
		token = self.session.cookies.get_dict()["csrftoken"]
		req = requests.Request("POST",
		                       self.contest_url + "problems/add?key=problemset_source",
		                       headers={"Referer" : self.szkopul},
		                       data={"csrfmiddlewaretoken" : token,
		                             "url_key" : url_key})
		prepared = self.session.prepare_request(req)
		self.session.send(prepared)

		self.__myPrint("Odczytywanie ID dodanego zadania")
		site = self.session.get(self.contest_problems_url)
		bs = BeautifulSoup(self.__htmlPreprocess(site.text), "html5lib")
		task_ID = sorted([(int(i.a["href"][35 + len(self.contest_name) : -8]), i.next_sibling.string) \
		                  for i in bs.findAll(class_="field-name_link")])[-1]
		return str(task_ID[0]), task_ID[1]
		
	def __getTestData(self, task_ID, short):
		if self.loged == False:
			self.__login()
		self.__myPrint("Odczytywanie informacji na temat testów i dodawanie zadania do rundy")
		link = self.contest_problems_url + task_ID + "/change"
		site = self.session.get(link)
		token = self.session.cookies.get_dict()["csrftoken"]
		bs = BeautifulSoup(self.__htmlPreprocess(site.text), "html5lib")

		form = {}
		ret = []

		test_num = 0
		for i in bs.find(class_="table table-condensed table-hover").tbody.findAll("tr"):
			if i.attrs.get("class", [""])[0] == "hidden":
				continue
			
			ls = i.findAll("td")

			name = ls[0].string
			time = ls[1].input["value"]
			memory = ls[2].input["value"]
			points = ls[3].input["value"]
			in_url = ls[5].p.a["href"]
			out_url = ls[6].p.a["href"]
			test_id = i.findAll("input")[-1]["value"]
			ret.append((name, time, memory, points, self.szkopul + in_url,
			            self.szkopul + out_url))

			form["test_set-" + str(test_num) + "-time_limit"] = time.strip()
			form["test_set-" + str(test_num) + "-memory_limit"] = memory.strip()
			form["test_set-" + str(test_num) + "-max_score"] = points.strip()
			form["test_set-" + str(test_num) + "-is_active"] = "on"
			form["test_set-" + str(test_num) + "-problem_instance"] = task_ID.strip()
			form["test_set-" + str(test_num) + "-id"] = test_id.strip()
			test_num += 1

		if self.info["memoryLimit"] == "":
			self.info["memoryLimit"] = str(int(ret[0][2]) // 1024) + " MB"

		form["round"] = self.round_id
		form["short_name"] = short.strip()
		form["submissions_limit"] = "10"
		form["_save"] = "Zapisz"
		form["test_set-TOTAL_FORMS"] = str(test_num)
		form["test_set-INITIAL_FORMS"] = str(test_num)
		form["test_set-MIN_NUM_FORMS"] = "0"
		form["test_set-MAX_NUM_FORMS"] = "0"
		form["test_set-__prefix__-time_limit"] = ""
		form["test_set-__prefix__-memory_limit"] = ""
		form["test_set-__prefix__-max_score"] = "10"
		form["test_set-__prefix__-is_active"] = "on"
		form["test_set-__prefix__-problem_instance"] = task_ID.strip()
		form["test_set-__prefix__-id"] = ""
		form["csrfmiddlewaretoken"] = token

		req = requests.Request("POST", link, headers={"Referer" : self.szkopul}, data=form)
		prepared = self.session.prepare_request(req)

		res = self.session.send(prepared)
		bs = BeautifulSoup(self.__htmlPreprocess(res.text), "html5lib")

		return ret

	def __getSolutions(self, task_ID):
		if self.loged == False:
			self.__login()
		self.__myPrint("Pobieranie rozwiązań")
		link = self.contest_url + "problem/" + task_ID + "/models"
		site = self.session.get(link)
		bs = BeautifulSoup(self.__htmlPreprocess(site.text), "html5lib")

		solid = [self.szkopul + i["href"] + "download/" for i in bs.find("thead").findAll("a")]

		self.__makeDir(self.prog_dir)
		main_sol = ""
		for i in solid:
			file = self.session.get(i, stream=True)
			solname = (file.headers["Content-Disposition"].split("=")[1])[1:-1]
			self.__myPrint("Pobieranie " + solname, indent=1)
			if (os.path.splitext(solname)[1] == ".cpp" or os.path.splitext(solname)[1] == ".c" or
			    os.path.splitext(solname)[1] == ".pas") and main_sol == "":
				main_sol = solname

			with open(self.prog_dir + solname, "wb") as handle:
				for block in file.iter_content(1024):
					handle.write(block)
		return main_sol

	def __deleteProblem(self, task_ID):
		if self.loged == False:
			self.__login()
		self.__myPrint("Usuwanie zadania ze szkopuła")
		link = self.contest_problems_url + task_ID + "/delete"
		site = self.session.get(link)
		token = self.session.cookies.get_dict()["csrftoken"]
		req = requests.Request("POST", link, headers={"Referer" : self.szkopul},
		                                     data={"csrfmiddlewaretoken" : token, "post" : "yes"})
		prepared = self.session.prepare_request(req)
		self.session.send(prepared)

	def __downloadInput(self, test_data):
		if self.loged == False:
			self.__login()
		self.__myPrint("Pobieranie plików in")
		self.__makeDir(self.in_dir)
		for i in test_data:
			file = self.session.get(i[4], stream=True)
			testname = os.path.basename((file.headers["Content-Disposition"].split("=")[1])[1:-1])

			self.__myPrint("Pobieranie " + testname, indent=1)

			with open(self.in_dir + testname, "wb") as handle:
				for block in file.iter_content(1024):
					handle.write(block)

	def __downloadOutput(self, test_data):
		if self.loged == False:
			self.__login()
		self.__myPrint("Pobieranie plików out")
		self.__makeDir(self.out_dir)
		for i in test_data:
			file = self.session.get(i[5], stream=True)
			testname = os.path.basename((file.headers["Content-Disposition"].split("=")[1])[1:-1])

			self.__myPrint("  Pobieranie " + testname)

			with open(self.out_dir + testname, "wb") as handle:
				for block in file.iter_content(1024):
					handle.write(block)

	def __generateOutput(self, sol, test_data):
		self.__myPrint("Generowanie plików out")
		self.__myPrint("Kompilowanie " + sol, indent=1)
		if os.path.splitext(sol)[1] == ".cpp":
			subprocess.call(["g++ " + self.prog_dir + sol + " -o " + self.prog_dir + "a.out -std=c++17 -O2"],
			                shell=True, stdout=self.OUT, stderr=self.OUT)
		elif os.path.splitext(sol)[1] == ".c":
			subprocess.call(["gcc " + self.prog_dir + sol + " -o " + self.prog_dir + "a.out -std=c11 -O2"],
				             shell=True, stdout=self.OUT, stderr=self.OUT)
		elif os.path.splitext(sol)[1] == ".pas":
			subprocess.call(["fpc " + self.prog_dir + sol + " -oa.out -O2 -XS -Xt"],
				             shell=True, stdout=self.OUT, stderr=self.OUT)

		self.__makeDir(self.out_dir)
		for i in test_data:
			nm = self.info["prefix"] + i[0]
			line = "ulimit -s 1048576 ; " + self.prog_dir \
			     + "a.out < " + self.in_dir + nm + ".in > " + self.out_dir + nm + ".out"
			self.__myPrint("Generowanie " + nm + ".out", indent=1)
			subprocess.call([line], shell=True, stdout=self.OUT)

	def __createConfig(self, test_data, limits):
		self.__myPrint("Tworzenie pliku konfiguracyjnego")
		save = ""
		save += "name: " + self.info["problemName"] + "\n"
		save += "label: " + self.info["prefix"] + "\n"
		save += "memory_limit: " + self.info["memoryLimit"].split(" ")[0] + "\n"

		# scoring
		save += "scoring: [\n"
		prev = ""
		for i in test_data:
			if i[0].find("ocen") != -1:
				continue
			tm = i[0]
			while tm[-1].isalpha():
				tm = tm[:-1]
			if tm != prev:
				prev = tm
				save += "  " + tm + " " + i[3] + "\n"
		save += "]\n"

		if limits:
			save += "limits: [\n"
			for i in test_data:
				save += "  " + self.info["prefix"] + i[0] + " " + str(float(i[1]) / 1000) + "\n"
			save += "]\n"

		# tests directories
		save += "tests_files: [\n"
		for i in test_data:
			tm_name = self.info["prefix"] + i[0]
			save += "  " + tm_name + " in/" + tm_name + ".in out/" + tm_name + ".out\n"
		save += "]\n"

		with open(self.task_dir + "/Simfile", "w") as file:
			file.write(save)

	def __printSearch(self, search):
		self.__myPrint("Znaleziono:")
		for i in search:
			self.__myPrint("Index: " + i[0], indent=1)
			self.__myPrint("Label: " + i[1], indent=1)
			self.__myPrint("Nazwa: " + i[2], indent=1)
			self.__myPrint("Tagi: " + i[3], indent=1)
			self.__myPrint("Hash: " + i[4] + "\n", indent=1)
		self.__myPrint("Liczba zadań spełniających podane warunki: " + str(len(search)))

	# constructors, destructors

	def __init__(self, username, password, contest_name, round_id, verbose=False, quiet=False):
		self.session = requests.Session()
		self.loged = False
		self.info = {}
		self.quiet = quiet

		self.username = username
		self.password = password
		self.contest_name = contest_name
		self.round_id = round_id
		
		# aliases
		self.szkopul = "https://szkopul.edu.pl/"
		self.login_url = self.szkopul + "login/"
		self.problemset_url = self.szkopul + "problemset/"
		self.contest_url = self.szkopul + "c/" + self.contest_name + "/"
		self.contest_problems_url = self.contest_url + "admin/contests/probleminstance/"

		if quiet or verbose == False:
			self.OUT = open(os.devnull, "w")
		else:
			self.OUT = None

	def __del__(self):
		self.session.close()
		if self.OUT:
			del self.OUT

	# public

	# update task list
	def updateList(self):
		site = self.session.get(self.problemset_url)
		bs = BeautifulSoup(self.__htmlPreprocess(site.text), "html5lib")
		page_num = int(bs.find("ul", class_="pagination").findAll("li")[-2].string)

		task_id = 1
		with open("zadanka.txt", "w") as file:
			for page_num in range(1, page_num + 1):
				self.__myPrint("Aktualizowanie strony " + str(page_num))

				site = self.session.get(self.problemset_url + "?page=" + str(page_num))
				bs = BeautifulSoup(self.__htmlPreprocess(site.text), "html5lib")

				for i in bs.table.tbody.findAll("tr"):
					g = i.findAll("td")
					file.write(str(task_id) + "\n")

					task_id += 1
					file.write(g[0].string + "\n")

					if g[1].string.find("Zadanie ") == 0:
						file.write(g[1].string[8:] + "\n")
					elif g[1].string.find("Task ") == 0:
						file.write(g[1].string[5:] + "\n")
					else:
						file.write(g[1].string + "\n")

					tags = []
					for j in g[2].findAll("a"):
						tags.append(j.string)

					file.write(" ".join(tags) + "\n")
					file.write(g[1].a.get("href")[20:44] + "\n\n")

	# search tasks using given filters
	def searchTaskList(self, num=None, label=None, name=None, tag=None, neng=None):
		if tag:
			tag = tag.split()

		ls = []
		with open("zadanka.txt", "r") as file:
			while True:
				line = file.readline()
				if not line:
					break
				ls.append((line.strip(), file.readline().strip(), file.readline().strip(),
				           file.readline().strip(), file.readline().strip()))
				file.readline()

		if num:
			ls = [x for x in ls if x[0] == num]
		if label:
			ls = [x for x in ls if x[1] == label]
		if name:
			ls = [x for x in ls if x[2].lower().find(name.lower()) != -1]
		if tag:
			for i in tag:
				ls = [x for x in ls if x[3].lower().find(i.lower()) != -1 ]
		if neng:
			ls = [x for x in ls if x[3].lower().find("eng") == -1]

		return ls

	def gen(self, argv):
		search = self.searchTaskList(num=argv.id, label=argv.label, name=argv.name, tag=argv.tag, neng=argv.eng)
		self.__printSearch(search)

		if len(search) != 1:
			self.__myPrint("Liczba znalezionych zadań nie jest równa 1")
			return 1
		else:
			search = search[0]

		if argv.generate:
			argv.input = argv.solutions = True
		if argv.limits:
			argv.config = True

		self.info["prefix"] = search[1]
		self.info["problemName"] = search[2]
		self.info["additionalFooterInfo"] = argv.footer
		self.info["contestName"] = argv.contest
		self.info["roundDate"] = argv.date
		self.info["inter"] = ""
		if argv.memory:
			self.info["memoryLimit"] = argv.memory.split(" ")[0] + " MB"
		else:
			self.info["memoryLimit"] = ""

		self.task_dir = self.__tooFileName(search[2]) + "-" \
		              + self.__tooFileName(search[3]) + "-" \
		              + self.__tooFileName(self.info["prefix"])
		self.latex_dir = self.task_dir + "/utils/latex/"
		self.latex_file = self.info["prefix"] + ".tex"
		self.pdf_dir = self.task_dir + "/doc/"
		self.pdf_file = self.info["prefix"] + ".pdf"
		self.in_dir = self.task_dir + "/in/"
		self.out_dir = self.task_dir + "/out/"
		self.prog_dir = self.task_dir + "/prog/"
		self.problem_url = self.problemset_url + "problem/" + search[4]

		if argv.pdf:
			self.__getStatement()

		if argv.input or argv.output or argv.generate or argv.solutions or argv.config or argv.limits:
			task_ID, short = self.__addProblem(search[4])
			test_data=self.__getTestData(task_ID, short)
			if argv.solutions:
				main_sol = self.__getSolutions(task_ID)
			if argv.input:
				self.__downloadInput(test_data)
			if argv.output:
				self.__downloadOutput(test_data)
			if argv.generate:
				self.__generateOutput(main_sol, test_data)
			if argv.config:
				self.__createConfig(test_data, argv.limits)
			self.__deleteProblem(task_ID)
		
		if argv.zip:
			self.__createArchive()

	def search(self, argv):
		search = self.searchTaskList(num=argv.id, label=argv.label, name=argv.name, tag=argv.tag, neng=argv.eng)
		self.__printSearch(search)

if __name__ == "__main__":
	paczkarka = Paczkarka(username, password, contest_name, round_id, verbose=argv.verbose, quiet=argv.quiet)
	if argv.type == "update":
		paczkarka.updateList()
	elif argv.type == "gen":
		paczkarka.gen(argv)
	elif argv.type == "search":
		paczkarka.search(argv)
