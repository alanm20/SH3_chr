# SH3_chr
Silent Hill 3 character loader and mdl exporter for Noesis
-  Import silent hill 3 character to Noesis for exporting to Blender 3D
-  Supports bones/skeleton
-  Export modfied glTF 2.0  model back to mdl so it can be loaded in Silent Hill 3 game

Installation:
- Put fmt_SH3_mesh.py in  Noesis plugins/python/   directory

Acknowledgements:
-  Rich Whitehouse : Noesis platform, which made all these possible
-  Gh0stBlade : The original Tomb Raider 8 Noesis mesh loader code
-  AlphaZomega : Inspired by his ROTTR mesh modding method and tool. mdl writer is based on his tr2mesh writer function  
-  Murugo : Misc-Game-Research github artifacts especially information on PS2 Silent Hill 2/3 game file format
-  HenryOfCarim and Sebastian Brachi: Albam Reloaded Blender addon. Use their tri-list to tri-strip conversion code.  

Disclaimer:
This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable for any damages arising from the use of this software. 

How to use:
-  Extract game arc file to get character mdl file.  A copy of SH2,3 Explorer v0.8 can be found in this Russian site: 
 ([http://heather.ucoz.ru/load/29-1-0-72])
-  In SH2,3 Explorer choose "Add file" menu and open "Silent Hill 3/Data/arc.arc" file. Expand the directory tree in the left panel to find Root->arc.arc->data->chrpl.arc. Left click on chrpl.arc to select it, then right click on chrpl.arc and choose "Extract Selection"
-  Extracted files are stored under "Silent Hill 3/data/data" folder 
- Run Noesis.exe and navigate to "Silent Hill 3/data/data/chr/pl/pcchr/pl/"  and click on "chhaa.mdl" (Heather starting outfit) to load it in Noesis.

To export character to Blender 3.x:
-   Use Noesis File|Export Preview and set file format to ".gltf (glTF Model)" format ( other formats may not export materials correctly)
-   In Blender use File|Import and select glTF 2.0 (.glb/.gltf) import option to import .glf model file

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/export.png?raw=true)
![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/import.png?raw=true)


Character modding (not so detail) instructions: 

Use Heather starting outfit (chhaa.mdl) as example. New outfit converted from [Sasuke-Bby]'s XPS file (https://www.deviantart.com/sasuke-bby/art/Silent-Hill-3-Heather-Open-Jacket-for-XPS-756352701) 

Overviews:

1. load chhaa.mdl to Noesis and export it to glTF format.
2. Start Blender 3.X and delete all object in the start up scene (no camera, no lights). Import glTF file. Select and make a duplication of all body meshes(exclude armature).
3. Join all duplicated meshes into one mesh and name it "weight source". This is used as bone weight transfer source.
4. load replacement outfit meshes. usually from wavefront OBJ format. Scale and move new meshes to align it with Heather body. Make sure each mesh can only use one material texture (game does not support multi-texture per mesh). OBJ import addon have a group by "material" option that neatly divide the mesh.
5. select "weight source" mesh and hold down shift and select one new outfit mesh. Switch to weight paint mode and click on "Weights" menu drop down and select "Transfer weights" menu item.
6. Click on "Transfer Mesh Data" panel bar to see detail options, set "Vertex Mapping"->"Nearest face interpolated", "Ray Radius"-> "1m" , "Source layer selection" -> "By Name", "Destination layer" -> "All Layers".
7. Click on "Weights" menu again and choose "Limit Total". Set limit to "3" (default is 4). Game only support 3 bones weight per vertex.
8. Switch back to object mode. repeat step 5,6,7 for each new outfit mesh to give all of them bone weights.  
9. suppose new outfit has 3 meshes. you need to find and replace 3 meshes in Heather model. In Blender outliner panel click on the + icon of a mesh to see the mesh data block (upside down triangle icon) name. It will have name like "Mesh_0_?". suppose Mesh_0_3, Mesh_0_6 , Mesh_0_11 are original outfit mesh. write down these name and you can delete these 3 meshes. next step will replace them with new mesh.
10. expand the new outfit mesh + icon. and right click on mesh data block and choose rename. Give the 3 new outfit mesh the name Mesh_0_3, Mesh_0_6 and Mesh_0_11.
11. If you still have old outfit meshes that you don't need. just simply delete that old mesh. You cannot add new mesh. Can only replace or delete existing one.
12. Hide the "weight source" object and any object that does not belong to the character, make sure armature is visible. Choose File menu/Export/glIF 2.0 format.
13. Set these export option:. Format->"glTF separate(.gltf + .bin + textures)", Include->Limit to: check "Visble Objects", "Mesh"-> Check "Apply Modifiers"
14. Specify a file name and a new folder location and click on "Export glTF 2.0" button to export.
15. In Noesis , navigate to and load new exported glTF file. you should see the modified outfit. Choose "Export from Preview" and select a new destiantion folder and file name (chhaa.mdl in this case )for the exported mdl. Set "Main output type" to ".mdl - Silent Hill 3 3D Mesh (PC)". Click on "Export" button. You will see a prompt asking the file location of the original mdl you are replacing. Choose "Browse" and  navigate and select "Silent Hill 3/data/data/pcchar/pl/chhaa.mdl". click ok to export.
16. Check for errors in the export message box. Typical error would be mdl exporter found vertex with more than 3 bone weights in the new mesh, which you need to make sure you set Bone weight "Limit Total" to 3 in Blender.
17. Backup all your Silent Hill 3/data/*.arc files.  Use SH2,3 Explorer v0.8 to import new chhaa.mdl and replace the  original chhaa.mdl in chrpl.arc.
18. Start a new game or load the first scene to see whether you get the mod working correctly.

Important notes: 
- If a material's texture was modified, material name cannot starts with the default "Mat_". Change it to something like "xMat_". Noesis exporter retains the original texture with "Mat_" marterial.
- Head/mouth/hair/eyes have morph shapes. Morphs will be disabled when replaced by a new mesh.


Default Heather (chhaa.mdl)

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/default%20heather.png)
Duplicate and combine meshes to one weight source mesh

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/weight%20source.png)
New outfit from OBJ import, divided into one material per mesh. Scaled and moved to overlap default heather model 

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/new%20outfit%20from%20OBJ.png)
Transfer weight operation and settings

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/transfer%20weight.png)
New mesh renamed to replace original mesh. Notice "Mesh_0_?" new mesh block name. Weight source mesh is hidden ( grayed out)

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/ready%20to%20export.png)
Blender glTF 2.0 export settings

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/Blender%20glTF%20export.png)

Noesis Mdl exporting setting, Set the destination file name and output type to mdl - "Silent Hill 3 (PC)". During export a prompt will ask for the original mdl file to export over.

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/noesis%20mdl%20export.png)

New outfit in game

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/in%20game.png)


Special Options:

Change the following flags in the loader source code to enable morph target loading. Set bMorph_calalog to 1 will shows Heather's all 25 morph shapes   

- bLoadMorph     = 0                ----->  1 = load morph target
- bMorph_catalog = 0              -----> 1 = display morphs as side-by-side meshes. 0 = morphs as frame

![alt text](https://github.com/alanm20/SH3_chr/blob/main/images/morph_gallery.png)
