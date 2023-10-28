# SH3_chr
Silent Hill 3 character loader for Noesis
-  Import silent hill 3 character to Noesis for exporting to Blender 3D.
-  Supports bones/skeleton 

Installation:
- Put fmt_SH3_mesh.py in  Noesis plugins/python/   directory

How to use:
-  Extract game arc file to get character mdl file.  A copy of SH2,3 Explorer v0.8 can be found in this Russian site([http://heather.ucoz.ru/load/29-1-0-72])
-  In SH2,3 Explorer choose "Add file" menu and open "Silent Hill 3/Data/arc.arc" file. Expand the directory tree in the left panel to find Root->arc.arcdata->chrpl.arc. Left click on chrpl.arc to select it, then right click on chrpl.arc and choose "Extract Selection"
-  Extracted files are stored under "Silent Hill 3/data/data" folder 
- Run Noesis.exe and navigate to "Silent Hill 3/data/data/chr/pl/pcchr/pl/"  and click on "chhaa.mdl" (Heather starting outfit)

To export character to Blender 3.x:
-   Use Noesis File|Export Preview and set file format to ".gltf (glTF Model)" format ( other formats may not export materials correctly)
-   In Blender use File|Import and select glTF 2.0 (.glb/.gltf) import option to import .glf model file

Disclaimer:
This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable for any damages arising from the use of this software. 


![alt text](https://github.com/alanm20/SH3_chr/blob/main/export.png)
![alt text](https://github.com/alanm20/SH3_chr/blob/main/import.png)
