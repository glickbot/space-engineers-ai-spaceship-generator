pyinstaller comparator_webapp_launcher.py ^
	--clean ^
	--onefile ^
	--noconfirm ^
	--name "Spaceships Comparator" ^
	--icon assets\comparator\favicon.ico ^
	--add-data "./estimators;estimators" ^
	--add-data "./assets/comparator;assets" ^
	--add-data "./block_definitions.json;." ^
	--add-data "./common_atoms.json;." ^
	--add-data "./configs.ini;." ^
	--add-data "./hl_atoms.json;." ^
	--add-data "./hlrules;." ^
	--add-data "./llrules;."