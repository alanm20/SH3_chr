# SH3_chr
Silent Hill 3 character loader for Noesis
-  Import silent hill 3 character to Noesis for exporting to Blender 3D.
-  Supports bones/skeleton 

Installation:
- Put fmt_SH3_mesh.py in  Noesis plugin/python/   directory

- How to use
-  Find Silent Hill 3 PC  character archive files under inside game data/ directory. File name "chr*.arc" .i.e.  chrpl.arc, chren.rac chrch.arc , chrit.arc chrwp.arc
-  Extract arc file to a output directory using QuickBMS and "SH3 ARC bms script"
-    (https://wiki.xentax.com/index.php/Silent_Hill_3_ARC)
-    i.e  quickbms.exe silent_hill_3.bms chrpl.arc  C:\output_dir
- Run Neosis.exe and navigate to output_dir and click on the characater .dat file
- Some .dat are not character model so Noesis will give warnings says they cannot be loaded

- To export character to Blender 3.x.
-   Use Noesis File|Export Preview and set file format to ".gltf (glTF Model)" format ( other formats may not export materials correctly)
-   In Blender use File|Import and select glTF 2.0 (.glb/.gltf) import option to import .glf model file
