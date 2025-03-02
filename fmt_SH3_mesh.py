#
# Silent Hill 3 PC Model loader
# alanm1
# v0.3 allow replacement of mesh with morphs by default (face,mouth and hair). New mesh is static with no morph animation
# v0.2 add code to prevent modification to mesh with morph. no support for modifying morph target
# v0.1 initial release

#
#Based on:
#Tomb Raider: Underworld/Lara Croft and The Guardian Of Light [PC/X360] - ".tr8mesh" Loader
#By Gh0stblade
#v2.4
#Special thanks: Chrrox
# 
# Mdl writer based on alphaZOmega's tr2mesh exporter
#

#Options: These are bools that enable/disable certain features! 
#Var                            Effect
#Misc
#Mesh Global
bLoadMorph  =  0                # 1 = load morph target
bMorph_catalog = 0              # 1 = display morphs as side-by-side meshes. 0 = morphs as frame
Morph_spacing = 100

fDefaultMeshScale = 1.0         #Override mesh scale (default is 1.0)
bOptimizeMesh = 0               #Enable optimization (remove duplicate vertices, optimize lists for drawing) (1 = on, 0 = off)
bMaterialsEnabled = 1           #Materials (1 = on, 0 = off)
bRenderAsPoints = 0             #Render mesh as points without triangles drawn (1 = on, 0 = off)
#Vertex Components
bNORMsEnabled = 1               #Normals (1 = on, 0 = off)
bUVsEnabled = 1                 #UVs (1 = on, 0 = off)
bCOLsEnabled = 0                #Vertex colours (1 = on, 0 = off)
bSkinningEnabled = 1            #Enable skin weights (1 = on, 0 = off)
#Gh0stBlade ONLY
debug = 0                       #Prints debug info (1 = on, 0 = off)
bDumpTris = 0                   #Dump triangles to binary file

from inc_noesis import *
import math
import glob
import re
import copy
from operator import itemgetter, attrgetter
from collections import deque, namedtuple
from io import *
    
def registerNoesisTypes():
    handle = noesis.register("Silent Hill 3: 3D Mesh [PC]", ".mdl")
    noesis.setHandlerTypeCheck(handle, meshCheckType)
    noesis.setHandlerLoadModel(handle, meshLoadModel)
    noesis.setHandlerWriteModel(handle, meshWriteModel)

    handle = noesis.register("Silent Hill 3: 2D Texture [PC]", ".dat")
    noesis.setHandlerTypeCheck(handle, rawTexCheckType)
    noesis.setHandlerLoadRGBA(handle, rawTexLoad)
    
    #noesis.logPopup()
    return 1
    
def rawTexCheckType(data):
    bs = NoeBitStream(data)
    magic = bs.readUInt()
    if magic == 0xFFFFFFFF:
        return 1
    else: 
        print("Fatal Error: Unknown file magic: " + str(hex(magic) + " expected 0xFFFFFFFF!"))
        return 0
def rawTexLoad(data, texList):
    bs = NoeBitStream(data)
    texStart = bs.tell()
    bs.seek(0x8,NOESEEK_REL)
    ddsWidth = bs.readUShort()
    ddsHeight= bs.readUShort()
    unk = bs.readUInt()
    ddsSize = bs.readUInt()
    dataOffset = bs.readUShort()    
    bs.seek(texStart+dataOffset, NOESEEK_ABS)
    if debug:
        print("rawTexure",ddsWidth,ddsHeight)
    ddsData = bs.readBytes(ddsSize)
    ddsData = rapi.imageDecodeRaw(ddsData, ddsWidth, ddsHeight, "b8g8r8a8")
    ddsFmt = noesis.NOESISTEX_RGBA32
    texList.append(NoeTexture("Texture", ddsWidth, ddsHeight, ddsData, ddsFmt))
    return 1
    
def meshCheckType(data):
    bs = NoeBitStream(data)
    ### skip extra header
    uiUnk = bs.readUInt();
    bs.readByte();
    sig = bs.readByte();  # no good way to check for SH3 mdl file.
    #if sig != 0x01 and sig != 0x02 and sig !=0x10:
    #    return 0
    bs.seek(20, NOESEEK_ABS)
    mesh_start = bs.readUInt();
    if mesh_start > len(data):
        return 0
    bs.seek(mesh_start, NOESEEK_ABS)
    uiMagic = bs.read("I")
    
    global iPlatform
    global iMeshType
    
    iPlatform = -1
    iMeshType = -1
    
    if uiMagic[0] == 0xFFFF0003:
        if debug:
            print("Render Mesh LE!")
        iPlatform = 0#PC
        iMeshType = 0#RenderMesh
        return 1      
    else:
        print("Fatal Error: Unsupported Mesh header! " + str(uiMagic))
    return 0

def sh3LoadMDLTex(bs, num_tex, texList):
    bs.seek(12,NOESEEK_ABS)
    texs_offset = bs.readUInt()
    bs.seek(texs_offset+0x20,NOESEEK_ABS)
    for i in range(num_tex):
        texStart = bs.tell()
        print ("tell ",hex(texStart))
        bs.seek(0x8,NOESEEK_REL)
        ddsWidth = bs.readUShort()
        ddsHeight= bs.readUShort()
        unk = bs.readUInt()
        ddsSize = bs.readUInt()
        dataOffset = bs.readUShort()
        
        bs.seek(texStart+dataOffset, NOESEEK_ABS)

        texName = "Tex_"+str(i)
        if debug:
            print(texName,ddsWidth,ddsHeight)
        print(texName,ddsWidth,ddsHeight,ddsSize)
        ddsData = bs.readBytes(ddsSize)
        ddsData = rapi.imageDecodeRaw(ddsData, ddsWidth, ddsHeight, "b8g8r8a8")
        ddsFmt = noesis.NOESISTEX_RGBA32

        texList.append(NoeTexture(texName, ddsWidth, ddsHeight, ddsData, ddsFmt))

class meshFile(object):
    
    def __init__(self, data):
        self.inFile = None
        self.texExtension = ""
        
        if iPlatform == 0: 
            self.inFile = NoeBitStream(data)
            self.texExtension = ".tr8pcd9"
        elif iPlatform == 1:
            self.inFile = NoeBitStream(data, NOE_BIGENDIAN)
            rapi.rpgSetOption(noesis.RPGOPT_BIGENDIAN, 1)
            self.texExtension = ".tr8x360"
        else: 
            print("Fatal Error: Unknown Platform ID: " + str(iPlatform))
            
        self.fileSize = int(len(data))
        
        self.meshGroupIdx = 0
        self.offsetMeshStart = -1
        self.offsetStart = -1
        self.offsetMatInfo = -1
        self.numBones = -1
        self.numMeshes = 0
        self.offsetBones = 0
        self.offsetMeshes = 0
        self.offsetMeshes2 = 0
        self.numMeshes2 = 0

        self.offsetVertex = 0
        self.offsetFaceIdx = 0
        self.numVertices = 0
        self.offsetSkel = 0
        self.numBones2 = 0
        self.offsetSkel2 = 0
        self.offsetBones2 = 0
        self.morph_base_cnt = 0
        self.morph_base_offs = 0
        self.morph_data_cnt = 0
        self.morph_data_offs = 0
        
        self.bonePair = []
        self.meshOffsets = []
        self.boneList = []
        self.boneMap = []
        self.matList = []
        self.matNames = []
        self.texList = []
        self.texNames = []
        self.boneTrans = []
        self.boneMat = []
        self.boneMat2 = []
        self.matTable = []
        self.matHash = {}
        self.morph_targets = []
        
    def setMaterial(self, matId):
        texId = self.matTable[matId][0]
        texture = self.texList[texId]
        if matId in self.matHash:
            material = self.matHash[matId]
        else:
            matName = "Mat_"+str(matId)
            texName = "Tex_"+str(texId)
            material = NoeMaterial(matName,texName)
            # some models have flipped face vertex order
            material.setFlags(noesis.NMATFLAG_TWOSIDED, 0)   
            
            self.matList.append(material)
            self.matHash[matId] = material
            
        if bMaterialsEnabled != 0:    
            rapi.rpgSetMaterial(material.name)    

    def loadMesh(self):
        bs = self.inFile
        ### skip extra header
        
        bs.seek(8, NOESEEK_ABS)
        num_tex = bs.readUInt()
        
        if num_tex > 0:
            sh3LoadMDLTex( bs, num_tex, self.texList)
        
        bs.seek(20, NOESEEK_ABS)
        self.offsetMeshStart = bs.readUInt()
        bs.seek(self.offsetMeshStart,NOESEEK_ABS)
        
        uiMagic = bs.readUInt()
        uiUnk = bs.readUInt()
        self.offsetBones = bs.readUInt()
        self.numBones = bs.readUInt();
        self.offsetSkel = bs.readUInt();
        self.numBones2 = bs.readUInt()
        self.offsetBonePair = bs.readUInt()
        self.offsetBones2 = bs.readUInt()

        self.numMeshes = bs.readUInt();
        self.offsetMeshes = bs.readUInt()
        self.numMeshes2 = bs.readUInt()
        self.offsetMeshes2 = bs.readUInt()
        self.num_Material = bs.readUInt()
        bs.seek(4,NOESEEK_REL);
        self.num_matTableEntry = bs.readUInt()
        self.offset_matTable = bs.readUInt()
        bs.readUInt()  # unknown
        self.morph_base_cnt = bs.readUInt()
        self.morph_base_offs = bs.readUInt()
        self.morph_data_cnt = bs.readUInt()
        self.morph_data_offs = bs.readUInt()
        
        bs.seek( self.offsetMeshStart + self.offset_matTable);
        # build matID to texture mapping
        for i in range(self.num_matTableEntry):
            self.matTable.append( [bs.readUInt(),bs.readUInt()]) # texture ID, unknownID
              
        self.buildSkeleton() 
        # second bone list is a bonepair list, each entry is [main bone_id, secondary bone_id]
        # don't know why going through this trouble to store 2nd and third bone id.
        bs.seek( self.offsetMeshStart + self.offsetBonePair);
        for i in range(self.numBones2):
            self.bonePair.append([bs.readByte(),bs.readByte()])
        print ("bonepair table",self.bonePair)
        
        # build morph targets
        # Code based on Murugo's Misc-Game-Research github artifacts ,PS2 SH2/3 import_mod.py
        bs.seek(self.offsetMeshStart + self.morph_base_offs,NOESEEK_ABS)
        base_pos_int16 = []
        base_norm_int16 = []
        for i in range(self.morph_base_cnt):        
             base_pos_int16.append([bs.readShort(),bs.readShort(),bs.readShort()])             
             base_norm_int16.append([bs.readShort(),bs.readShort(),bs.readShort()])   

        bs.seek(self.offsetMeshStart + self.morph_data_offs,NOESEEK_ABS)
        morph_target_desc=[(bs.readUInt(),bs.readUInt()) for _ in range(self.morph_data_cnt)]        
        normList= []      
        for vcnt, offs in morph_target_desc:  
            print ("vcnt",vcnt,hex(offs))
            bs.seek(self.offsetMeshStart + offs,NOESEEK_ABS)
            pos_int16 = copy.deepcopy(base_pos_int16)
            norm_int16 = copy.deepcopy(base_norm_int16)

            for i in range(vcnt):
                a,b,c = (bs.readShort(),bs.readShort(),bs.readShort())
                d,e,f = (bs.readShort(),bs.readShort(),bs.readShort())
                delta_xyz = [a,b,c]
                delta_norm= [d,e,f]
                vidx = bs.readUShort()
                pos_int16[vidx][0]= base_pos_int16[vidx][0]+ delta_xyz[0]
                pos_int16[vidx][1]= base_pos_int16[vidx][1]+ delta_xyz[1]
                pos_int16[vidx][2]= base_pos_int16[vidx][2]+ delta_xyz[2]
                norm_int16[vidx][0]=base_norm_int16[vidx][0]+ delta_norm[0]
                norm_int16[vidx][1]=base_norm_int16[vidx][1]+ delta_norm[1]
                norm_int16[vidx][2]=base_norm_int16[vidx][2]+ delta_norm[2]  
 
            self.morph_targets.append((pos_int16,norm_int16))
        #for pos,_ in self.morph_targets:
        #    print("pos",pos[0x16])   
        '''    
        for norm in pos_int16:
            normList.append(norm[0]/4096)
            normList.append(norm[1]/4096)
            normList.append(norm[2]/4096)
                    
        morphPosAr = struct.pack("<" + 'f'*len(normList), *normList)
        rapi.rpgBindPositionBufferOfs(morphPosAr, noesis.RPGEODATA_FLOAT, 0xc, 0x0)
        rapi.rpgCommitTriangles(None, noesis.RPGEODATA_USHORT, self.morph_base_cnt, noesis.RPGEO_POINTS, 1)
        rapi.rpgClearBufferBinds()                                               
        ''' 
        # main meshes           
        self.loadMeshes(bs,0,self.numMeshes,self.offsetMeshes)
        #
		#tansparent hair meshes
        self.loadMeshes(bs,1,self.numMeshes2,self.offsetMeshes2)
        
    def loadMeshes(self, bs, meshGroup, numMeshes, offsetMeshes):
        cur_pos = self.offsetMeshStart + offsetMeshes;        
        for i in range(numMeshes):        
            bs.seek(cur_pos, NOESEEK_ABS)
            mesh_size = bs.readUInt()
            unk =  bs.readUInt()
            header_size = bs.readUInt()
            unk = bs.readUInt()
            unk = bs.readUInt()
            morph_ref_cnt = bs.readUInt()
            morph_ref_offs = bs.readUInt()
            num_bones = bs.readUInt()
            bonemap_offset = bs.readUInt()
            
            num_bones2 = bs.readUInt()
            bonemap_offset2 = bs.readUInt()
            
            bs.seek(3*4,NOESEEK_REL)
            
            mat_id_offset = bs.readUInt()

            bs.seek(2*4,NOESEEK_REL)
            num_vertex = bs.readUInt()
            fidx_offset = bs.readUInt()
            numFidx = bs.readUInt()
            
            
            if debug:
                print ("mesh ",meshGroup,i,hex(mesh_size),hex(header_size),num_bones,num_bones2,hex(num_vertex),hex(fidx_offset))
            bs.seek(cur_pos + bonemap_offset, NOESEEK_ABS)
            # construct bonemap            
            self.boneMap = []
            # mesh first bonemap, contains first bone b_id
            for b in range(num_bones):            
                self.boneMap.append(bs.readUShort())
            # mesh 2nd bonemap , contain bonepair index, use it to find bone pair and the real bond id
            bs.seek(cur_pos + bonemap_offset2, NOESEEK_ABS)    
            bonePairList =[]
            print ("bonemap",self.boneMap)
            for b in range(num_bones2):
                bonepair_idx = bs.readUShort()                
                # take the 2nd bone_id of the pair.
                bonePairList.append(self.bonePair[bonepair_idx])
                self.boneMap.append(self.bonePair[bonepair_idx][1])
            print ("bonemap",bonePairList)
            
            rapi.rpgSetBoneMap(self.boneMap)
            
            bs.seek (cur_pos + mat_id_offset, NOESEEK_ABS)
            mat_id = bs.readUShort()
                        
            # set up material
            self.setMaterial(mat_id)
            
            # advance to the vertex buffer
            bs.seek(cur_pos + header_size, NOESEEK_ABS)
                        
            if debug:
                print("Mesh Info Start: " + str(bs.tell()))
                print("Bonemap ",i,self.boneMap)
            meshFile.buildMesh(self, [num_vertex, cur_pos + fidx_offset, numFidx, meshGroup, morph_ref_cnt, cur_pos + morph_ref_offs], i, self.boneMap, self.offsetBones, self.offsetFaceIdx, self.numBones)
            if debug:
                print("Mesh Info End: " + str(bs.tell()))
            cur_pos = cur_pos + mesh_size
            
    def buildMesh(self, meshInfo, meshIndex, boneMap, uiOffsetBoneMap, uiOffsetFaceData, usNumBones):        
        bs = self.inFile        
        
        rapi.rpgSetName("Mesh_"+ str(meshInfo[3]) + "_" + str(meshIndex))
        rapi.rpgSetPosScaleBias((fDefaultMeshScale, fDefaultMeshScale, fDefaultMeshScale), (0, 0, 0))
        
        print ("Mesh_"+ str(meshInfo[3]) + "_" + str(meshIndex))
        ucMeshVertStride = 0x30
        iMeshVertPos = 0
        iMeshNrmPos = 28
        iMeshBwPos = 12
        iMeshBiPos = 24
        iMeshUV1Pos = 0x28
            
        cur_pos = bs.tell()
        ucMeshVertStride = int(( meshInfo[1]-cur_pos )/meshInfo[0])  # (fidx_offset - vertex_offset)/ num_vertex       
        if ucMeshVertStride == 0x20: # no bone info, static mesh
            iMeshNrmPos = 12
            iMeshUV1Pos = 0x18
        if debug:
            print("VertStride ",hex(ucMeshVertStride),"meshInfo: ",hex(meshInfo[0]),hex(meshInfo[1]),hex(meshInfo[2]))
            
        vertBuff = bs.readBytes(meshInfo[0] *ucMeshVertStride)

        bs.seek( meshInfo[1], NOESEEK_ABS)
        faceBuff = bs.readBytes(meshInfo[2]*4)         
        
        # flip mesh along y-axis (vertial direction)
        rapi.rpgSetTransform(NoeMat43((NoeVec3((-1, 0, 0)), NoeVec3((0, -1, 0)), NoeVec3((0, 0, 1)), NoeVec3((0, 0, 0)))))     

        normList = []
        vertList = []
        bwList = []
        biList = []
   
        for n in range(meshInfo[0]):
            vidx = ucMeshVertStride * n
            x,y,z = struct.unpack('fff', vertBuff[vidx:vidx+12])
            # need to moved vertex to initial postion
            if ucMeshVertStride == 0x20:  # static mesh , no bone info                
                nx,ny,nz = struct.unpack('fff', vertBuff[vidx+12:vidx+24])            
            else:             
                nx,ny,nz = struct.unpack('fff', vertBuff[vidx+28:vidx+40])            
                Bw1,Bw2,Bw3 = struct.unpack('fff',vertBuff[vidx+12:vidx+24])
                Bi1,Bi2,Bi3,Bi4 = struct.unpack('BBBB',vertBuff[vidx+24:vidx+28])
            
                Bi4 = 255   
                #if bone weight is 0.0, set bone id to 255(dummy). prevent weight export problem
                if Bw3 == 0.0:
                    Bi3 = 255
                    if Bw2 == 0.0:
                        Bi2 = 255            
                biList.append(Bi1)
                biList.append(Bi2)
                biList.append(Bi3)
                #biList.append(Bi4)

            vert = NoeVec4((x,y,z,1))
            norm = NoeVec4((nx,ny,nz,0))
            
            if ucMeshVertStride == 0x20:  # no skeleton             
                mat = self.boneMat[0]
            else:
                bid = boneMap[Bi1]
                mat = self.boneMat[boneMap[Bi1]]

            # transform vertices and normals to their inital positions
            newv = mat * vert
            newn = mat * norm
            vertList.append(newv[0])
            vertList.append(newv[1])
            vertList.append(newv[2])
            
            normList.append(newn[0])
            normList.append(newn[1])
            normList.append(newn[2])
            
        vertB = struct.pack("<" + 'f'*len(vertList), *vertList)        
        rapi.rpgBindPositionBufferOfs(vertB, noesis.RPGEODATA_FLOAT, 0xc, 0x0)

        normBuff = struct.pack("<" + 'f'*len(normList), *normList)        
        rapi.rpgBindNormalBufferOfs(normBuff, noesis.RPGEODATA_FLOAT, 0xC, 0x0)

        if ucMeshVertStride > 0x20:
            biBuff = struct.pack("<" + 'B'*len(biList), *biList)  
            rapi.rpgBindBoneIndexBufferOfs(biBuff, noesis.RPGEODATA_UBYTE, 3, 0, 0x3)                    
            rapi.rpgBindBoneWeightBufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshBwPos, 0x3)

        rapi.rpgBindUV1BufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshUV1Pos)
                
        if bLoadMorph and meshInfo[4] > 0: # number of morph refs
            if bMorph_catalog: # morph render as separated mesh
                rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_UINT, meshInfo[2], noesis.RPGEO_TRIANGLE_STRIP, 0x1)
        
            # fetch morph shapes and combine it with mesh shape to form morph frames
            bs.seek(meshInfo[5], NOESEEK_ABS)
            morph_refs = []
            for _ in range(meshInfo[4]):
                morph_refs.append((bs.readUShort(),bs.readUShort(),bs.readUShort()))

            morph_shift_x = -((len(self.morph_targets)+1)//2) * Morph_spacing
            # 
            # morph format based on Murugo's Misc-Game-Research github PS2 Silent Hill 3 file format
            #
            for pos_list, norm_list in self.morph_targets:   
                morphPos = copy.deepcopy(vertList)
                morphNrm = copy.deepcopy(normList)
                #print ("pos list", len(pos_list))
                for src_idx, dest_addr, cnt in morph_refs: 
                   # print ("src_idx",src_idx, dest_addr, cnt)
                    for c in range(cnt):
                        # morph vertex pos/normal also need to be transformed
                        vidx = (dest_addr + c )*ucMeshVertStride
                        Bi1,Bi2,Bi3,Bi4 = struct.unpack('BBBB',vertBuff[vidx+24:vidx+28])
                        if ucMeshVertStride == 0x20:  # no skeleton             
                            mat = self.boneMat[0]
                        else:
                            mat = self.boneMat[boneMap[Bi1]] 
                        pos = [v/0x10 for v in pos_list[src_idx + c]] # convert to float
                        pos = mat * NoeVec4([pos[0],pos[1],pos[2],1.0])
                        norm =[n/0x1000 for n in norm_list[src_idx + c]] # convert to float
                        norm = mat * NoeVec4([norm[0],norm[1],norm[2], 0.0])
                        morphPos[(dest_addr + c)*3] = pos[0]
                        morphPos[(dest_addr + c)*3+1] = pos[1]
                        morphPos[(dest_addr + c)*3+2] = pos[2]
                        morphNrm[(dest_addr + c)*3] = norm[0]
                        morphNrm[(dest_addr + c)*3+1] = norm[1]
                        morphNrm[(dest_addr + c)*3+2] = norm[2]
                        #print ("pos/norm",pos,norm)
                if bMorph_catalog:
                    shiftPos = []
                    for i, v  in enumerate(morphPos):
                        if i % 3 == 0:
                          shiftPos.append(v + morph_shift_x)
                        else:
                          shiftPos.append(v)
                    morphPosAr = struct.pack("<" + 'f'*len(shiftPos), *shiftPos)      
                else:
                    morphPosAr = struct.pack("<" + 'f'*len(morphPos), *morphPos)
                morphNrmAr = struct.pack("<" + 'f'*len(morphNrm), *morphNrm) 
                if  bMorph_catalog:    
                    rapi.rpgBindPositionBufferOfs(morphPosAr, noesis.RPGEODATA_FLOAT, 0xc, 0x0)
                    rapi.rpgBindNormalBufferOfs(morphNrmAr, noesis.RPGEODATA_FLOAT, 0xC, 0x0)
                    rapi.rpgBindUV1BufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshUV1Pos)

                    rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_UINT, meshInfo[2], noesis.RPGEO_TRIANGLE_STRIP, 0x1)
                    #rapi.rpgClearBufferBinds()   
                    morph_shift_x = morph_shift_x + Morph_spacing
                    if morph_shift_x == 0: 
                        morph_shift_x = morph_shift_x + Morph_spacing
                else:                
                    rapi.rpgFeedMorphTargetPositions(morphPosAr, noesis.RPGEODATA_FLOAT, 12)
                    rapi.rpgFeedMorphTargetNormals(morphNrmAr, noesis.RPGEODATA_FLOAT, 12)
                    rapi.rpgCommitMorphFrame(meshInfo[0]) # number of mesh vertices
            if not bMorph_catalog:
                rapi.rpgCommitMorphFrameSet()
                rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_UINT, meshInfo[2], noesis.RPGEO_TRIANGLE_STRIP, 0x1)
        else:
            rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_UINT, meshInfo[2], noesis.RPGEO_TRIANGLE_STRIP, 0x1)
              
        if bOptimizeMesh:
            rapi.rpgOptimize()
        rapi.rpgClearBufferBinds()                                               

    def getTailPos(self, PID, bonePID,bonePos):
        hasChild = False
        childBone = None    
        childList = []
        for i,bone in enumerate(bonePID):
            if bonePID[i] == PID:
                childList.append(bonePos[i])
                hasChild = True
        if hasChild:
            temp = NoeVec3([0.0,0.0,0.0])
            for childPos in childList:
                temp += childPos
            temp /= len(childList)
        else:
            temp = NoeVec3(bonePos[PID])
        return temp
        
    class bone:
        def __init__(self, x, y, z):
            self.pos = NoeVec3([x,y,z])
            self.tail = NoeVec3(pos)
            self.direction = NoeVec3()
        
        
    def buildSkeleton(self):
        bs = self.inFile
        
        BonePID = []
        BonePos = []
        bone_mm = []
        if self.numBones > 0:
            bs.seek(self.offsetSkel + self.offsetMeshStart, NOESEEK_ABS)
            for i in range(self.numBones):
                pid = bs.readByte()
                BonePID.append(pid)
               
            bs.seek(self.offsetBones + self.offsetMeshStart, NOESEEK_ABS)
            for i in range(self.numBones):           
                # read mesh initial matrix                
                mat = NoeMat44([[bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()]])
                self.boneMat.append(mat)
                BonePos.append([-mat[3][0],-mat[3][1],mat[3][2]])
                
            for i in range(self.numBones):
                # calcate bone head and tail
                tailPos = self.getTailPos(i,BonePID,BonePos)
                BoneDir = tailPos - NoeVec3(BonePos[i])
                BoneDir.normalize()
                #self.getRotMat(BonePos[i],tailPos)                
                
                quat = NoeQuat([0, 0, 0, 1])
                bone_mat = quat.toMat43()  
                
                mat = self.boneMat[i]
                bone_mat[0]=[mat[0][0],mat[0][1],mat[0][2] ]
                bone_mat[1]=[mat[1][0],mat[1][1],mat[1][2] ]
                bone_mat[2]=[mat[2][0],mat[2][1],mat[2][2] ]
                bone_mat[3]=[-mat[3][0],-mat[3][1],mat[3][2] ]
               # bone_mat[3]=[mat[3][0],-mat[3][1],mat[3][2] ]
               # bone_mat[3]= BonePos[i]
                bone_mm.append(bone_mat)
                self.boneList.append(NoeBone(i, "bone%03i"%i, bone_mat, None, BonePID[i]))

        if self.numBones2 > 0:
            BonePair = []
            helperMat = []
            bs.seek( self.offsetMeshStart + self.offsetBonePair, NOESEEK_ABS);
            for i in range(self.numBones2):
                BonePair.append([bs.readByte(),bs.readByte()])         

            bs.seek(self.offsetBones2 + self.offsetMeshStart, NOESEEK_ABS)

            for i in range(self.numBones2):           
                # read mesh initial matrix                
                mat = NoeMat44([[bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()]])
                
                quat = NoeQuat([0, 0, 0, 1])
                bone_mat = quat.toMat43()                
                
                bone_mat[0]=[mat[0][0],mat[0][1],mat[0][2] ]
                bone_mat[1]=[mat[1][0],mat[1][1],mat[1][2] ]
                bone_mat[2]=[mat[2][0],mat[2][1],mat[2][2] ]
                bone_mat[3]=[mat[3][0],mat[3][1],mat[3][2] ]
                new_mat = mat * self.boneMat[BonePair[i][1]]

def meshLoadModel(data, mdlList):
    ctx = rapi.rpgCreateContext()
    mesh = meshFile(data)
    if iMeshType == 0:
        mesh.loadMesh()
        #mesh.buildSkeleton()                    
    else:
        print("Fatal Error: Unknown mesh type: " + str(iMeshType))
    try:
        mdl = rapi.rpgConstructModel()
    except:
        mdl = NoeModel()
    if len(mesh.boneList):
        mdl.setBones(mesh.boneList)
    mdl.setModelMaterials(NoeModelMaterials(mesh.texList, mesh.matList))
    mdlList.append(mdl);
    #for mtrl in mdl.modelMats.matList:
    #    print (mtrl.name,mtrl.texName)
    #for tex in mdl.modelMats.texList:
    #    print (tex.name,tex.pixelType)
    #tex = mdl.modelMats.texList[1]
    #raw_data = rapi.imageEncodeRaw(tex.pixelData,tex.width,tex.height, "b8g8r8a8")   
    return 1

# code from Ablam Reloaded Blender addon (HenryOfCarim and Sebastian Brachi) 
def triangles_list_to_triangles_strip(mesh):
    """
    Export triangle strips from a blender mesh.
    It assumes the mesh is all triangulated.
    Based on a paper by Pierre Terdiman: http://www.codercorner.com/Strips.htm
    """
    # TODO: Fix changing of face orientation in some cases (see tests)
    edges_faces = {}
    current_strip = []
    strips = []
    joined_strips = []
    face_cnt = int(len(mesh.indices)/3)
    faces_indices = deque(p for p in range(face_cnt))
    done_faces_indices = set()
    current_face_index = faces_indices.popleft()
    process_faces = True
    face_edges = []
    face_verts = []
    
    # build per face vertex array  and edge edge from tri list
    tri_verts = deque(v for v in mesh.indices)
    while tri_verts:
        v1=tri_verts.popleft()
        v2=tri_verts.popleft()
        v3=tri_verts.popleft()
        if v2 > v1: 
            e1 = (v1,v2) 
        else: 
            e1 = (v2,v1)
        if v3 > v2: 
            e2 = (v2,v3) 
        else: 
            e2 = (v3,v2)
        if v3 > v1: 
            e3 = (v1,v3) 
        else: 
            e3 = (v3,v1)        
        face_edges.append([e1,e2,e3])        
        face_verts.append([v1,v2,v3])
    # edges_faces collect faces that share the same edge    
    for index, edges in enumerate(face_edges):
        for edge in edges:
            edges_faces.setdefault(edge, set()).add(index)

    while process_faces:
        current_face_verts = face_verts[current_face_index][:] 
        strip_indices = [v for v in current_face_verts if v not in current_strip[-2:]]
        if current_strip:
            face_to_add = tuple(current_strip[-2:]) + tuple(strip_indices)
            if face_to_add != current_face_verts and face_to_add != tuple(reversed(current_face_verts)):
                # we arrived here because the current face shares and edge with the face in the strip
                # however, if we just add the verts, we would be changing the direction of the face
                # so we create a degenerate triangle before adding to it to the strip
                current_strip.append(current_strip[-2])
        current_strip.extend(strip_indices)
        done_faces_indices.add(current_face_index)

        next_face_index = None
        possible_face_indices = {}
        for edge in face_edges[current_face_index]:
            if edge not in edges_faces:
                continue
            checked_edge = {face_index: edge for face_index in edges_faces[edge]
                            if face_index != current_face_index and face_index not in done_faces_indices}
            possible_face_indices.update(checked_edge)
        for face_index, edge in possible_face_indices.items():
            if not current_strip:
                next_face_index = face_index
                break
            elif edge == tuple(current_strip[-2:]) or edge == tuple(reversed(current_strip[-2:])):
                next_face_index = face_index
                break
            elif edge == (current_strip[-1], current_strip[-2]):
                if len(current_strip) % 2 != 0:
                    # create a degenerate triangle to join them
                    current_strip.append(current_strip[-2])
                next_face_index = face_index

        if next_face_index:
            faces_indices.remove(next_face_index)
            current_face_index = next_face_index
        else:
            strips.append(current_strip)
            current_strip = []
            try:
                current_face_index = faces_indices.popleft()
            except IndexError:
                process_faces = False

    prev_strip_len = 0
    # join strips with degenerate triangles
    for strip in strips:
        if not prev_strip_len:
            joined_strips.extend(strip)
            prev_strip_len = len(strip)
        elif prev_strip_len % 2 == 0:
            joined_strips.extend((joined_strips[-1], strip[0]))
            joined_strips.extend(strip)
            prev_strip_len = len(strip)
        else:
            joined_strips.extend((joined_strips[-1], strip[0], strip[0]))
            joined_strips.extend(strip)
            prev_strip_len = len(strip)
           
    # make sure joined_strip len is multiple of 4
    strip_len = len(joined_strips)
    padding = int((strip_len+3)/4)*4 - strip_len
    last_idx = joined_strips[-1]
    for n in range(padding):
        joined_strips.append(last_idx)
    return joined_strips

def writeImage(bs,tex):  # write SH3 BGRA32 format image
    raw_data = rapi.imageEncodeRaw(tex.pixelData,tex.width,tex.height, "b8g8r8a8")   
    bs.writeUInt(0xffffffff)
    bs.writeUInt(0)
    bs.writeShort(tex.width)
    bs.writeShort(tex.height)
    bs.writeUInt(0x00003018)
    bs.writeUInt(tex.width*tex.height*4)
    bs.writeUShort(0x0060) # header size
    bs.writeUShort((tex.width*tex.height*4)>>16)
    bs.writeUInt(0)
    bs.writeByte((tex.width>>8)+7)
    bs.writeByte((tex.height>>8)+7)
    bs.writeUShort(0x9999)
    bs.writeBytes(b'\x00' * (16*4))
    bs.writeBytes(raw_data)
        
# based on alphaZomega's tr2mesh exporter   
def meshWriteModel(mdl, bs):
    ctx = rapi.rpgCreateContext()
    print ("            ----Slient Hill 3 mesh Export----")

    def getExportName():
        global doBlendshapes
        doBlendshapes = False
        
        newMeshName = ((re.sub(r'\.mesh\..*', "", rapi.getInputName().lower()).replace(".meshout","")).replace(".fbx","").replace(".tr2mesh","").replace("out.",""))
        newMeshName = noesis.userPrompt(noesis.NOEUSERVAL_FILEPATH, "Export over (dat)", "Choose a SH3 mdl file to export over", newMeshName, None)
        if newMeshName == None:
            print("Aborting...")
            return
        if newMeshName.find(" -bs".lower()) != -1:
            newMeshName = newMeshName.replace(" -bs".lower(), "")
            print ("Exporting with blend-shapes...")
            doBlendshapes = True
            
        return newMeshName    

    newMeshName = getExportName()
    if newMeshName == None:
        return 0        
    print ("newMeshName=",newMeshName)
    newMesh = rapi.loadIntoByteArray(newMeshName)
    f = NoeBitStream(newMesh)
    uiUnk = f.readUInt()
    uiUnk = f.readUInt()
    num_images = f.readUInt()
    offset_image = f.readUInt()
    #f.readByte();
    #sig = f.readByte();  # no good way to check for SH3 mdl file.
    #if sig != 0x01 and sig != 0x02 and sig !=0x10:
    #    return 0
    f.seek(20, NOESEEK_ABS)
    offsetMeshStart = f.readUInt();
    if offsetMeshStart > len(newMesh):
        print("Fatal Error: not a valid mdl file")
        return 0
    f.seek(offsetMeshStart, NOESEEK_ABS)
    uiMagic = f.readUInt()     
    if uiMagic != 0xFFFF0003:
        noesis.messagePrompt("Not a SH3 mdl file.\nAborting...")
        return 0
    uiUnk = f.readUInt()
    offsetBones = f.readUInt()
    numBones = f.readUInt()
    offsetSkel = f.readUInt()
    
    numBones2_pos = f.tell()
    numBones2 = f.readUInt()    
    offsetBonePair = f.readUInt()
    offsetBones2 = f.readUInt()
    numMeshes = f.readUInt();
    offsetMeshes = f.readUInt()
    numMeshes2 = f.readUInt()
    meshes2_offset_pos = f.tell()
    offsetMeshes2 = f.readUInt()
    numTextures = f.readUInt()
    offsetTexture =  f.readUInt()
    numMtrls = f.readUInt()
    offsetMrtl = f.readUInt() 
    f.readUInt()
    numBaseVerts = f.readUInt()
    offsetBaseVert =  f.readUInt()
    numBlendData = f.readUInt()
    offsetBlendData =  f.readUInt()
    f.readUInt()
    offsetUnk1 = f.readUInt()
    offsetUnk2 = f.readUInt()
    offsetUnk3 = f.readUInt()

    bonePair = []    
    f.seek( offsetMeshStart + offsetBonePair);
    for i in range(numBones2):
        bonePair.append((f.readByte(),f.readByte()))
    #print("bonePair",bonePair)    
    BonePos = []
    boneMat = []
    invMat = []
    f.seek(offsetBones + offsetMeshStart, NOESEEK_ABS)
    print ("numbones",numBones)
    for i in range(numBones):           
        # read mesh initial matrix                
        mat = NoeMat44([[f.readFloat(),f.readFloat(),f.readFloat(),f.readFloat()],
            [f.readFloat(),f.readFloat(),f.readFloat(),f.readFloat()],
            [f.readFloat(),f.readFloat(),f.readFloat(),f.readFloat()],
            [f.readFloat(),f.readFloat(),f.readFloat(),f.readFloat()]])
        boneMat.append(mat)
        invMat.append(mat.inverse())        
        BonePos.append([mat[3][0],-mat[3][1],mat[3][2]])        

    #Clone beginning of base file
    f.seek(0, NOESEEK_ABS) 
    bs.seek(0, NOESEEK_ABS)
    
    # copy up to bonePair table
    bs.writeBytes(f.readBytes(offsetMeshStart + offsetBonePair))
    meshGroupStart_i = f.tell()
    meshGroupStart_e = bs.tell() 
    
    #Remove noesis duplicate names
    for mesh in mdl.meshes:
        ss = mesh.name.split('_')
        if ss[0].isnumeric():
            mesh.name = ss[1] + "_" + ss[2] + "_" + ss[3]
            i = 4
            while i < len(ss):  # keep rest of name, may contain material grp info
                mesh.name = mesh.name + "_" + ss[i]
                i = i + 1

    #Validate meshes are named correctly
    objToExport = []
    submeshes = []
    for i, mesh in enumerate(mdl.meshes):
        ss = mesh.name.split('_')
        if len(ss) >= 3:
            if ss[0] == 'Mesh' and ss[1].isnumeric() and ss[2].isnumeric():
                objToExport.append(i)
    print ("objToExport",objToExport)
    NumMeshGroups = 2
    meshInfo = []
    meshInfo.append([numMeshes])
    meshInfo.append([numMeshes2])
    for mg in range(NumMeshGroups):
        meshes = []
        for m in range(meshInfo[mg][0]):
            bFind = 0
            for s in range(len(objToExport)):                
                sName = mdl.meshes[objToExport[s]].name.split('_')
                #print("sName", sName)
                if sName[0] == 'Mesh' and int(sName[1]) == mg and int(sName[2]) == m:
                    meshes.append(copy.copy(mdl.meshes[objToExport[s]]))                    
                    bFind = 1
                    break
            if bFind == 0:
                meshes.append(NoeMesh([], [], "None", 0))
        submeshes.append(copy.copy(meshes))

    # map bone index to skeleton bone number
    bidxToSkel = {}
    for i,b in enumerate(mdl.bones):
        bid = ''.join(filter(str.isdigit, b.name))
        if bid:
            boneid = int(bid)
            bidxToSkel[i]=boneid
            
    # start generating meshes        
    f.seek(offsetMeshes + offsetMeshStart, NOESEEK_ABS)        
    meshBufList = []   # new meshes are first hold in buffers for later assembly
    newMtrlList = []   # new material not in original character
    newMGrpList = []
    #print(submeshes)
    # there are 2 meshgroups        
    for i in range(NumMeshGroups):
        if i==1 :
            mesh2_start = bs.tell()
        for m, mesh in enumerate(submeshes[i]):
            
            ms = NoeBitStream()  # mesh buffer bitStream
            meshBufList.append((i,ms))
            
            mesh_start = f.tell()
            header_start = ms.tell()            
            # copy mesh header up to start of bonemap
            mesh_header  = f.readBytes(0xa0)
            # parse original mesh header
            mesh_size,unk,header_size,unk_1,n_fidx,n_mph,mph_off,n_bone, b_off, \
                n_bone2, b_off2, unk_3, unk_4, n_mtrl, mtrl_off, he_off, v_off, n_vert, \
                f_off, n_fidx2 = struct.unpack_from("IIIIIIIIIIIIIIIIIIII",mesh_header)                                                       

            ms.writeBytes(mesh_header)
            ms.writeBytes(f.readBytes(b_off-0xa0)) # copy header till bonemap start
            
            print (mesh.name)
            
            #if n_mph > 0 and mesh.name.find("_pass")== -1:  # this mesh has morphs, we cannot replace it unless mesh name contains "_pass"
            #    ms.writeBytes(f.readBytes(mesh_size-b_off))  # keep original mesh and morphs 
            #    numVerts = n_vert    
            #    num_fidx = n_fidx2
            #    fidx_start = f_off
            #el
            if mesh.name is not "None":   # generate new mesh
                header_cur_pos = ms.tell()
                ms.seek(5*4, NOESEEK_ABS) #disable any morphs references, old morph will not work with new mesh
                ms.writeUInt(0)
                ms.seek(header_cur_pos,NOESEEK_ABS)
                
                numVerts = len(mesh.positions)
                vertexBoneInfo=[]
                boneSet = set()
                bonePairSet = set()    
                # scan all vertex and create boneMap, and bonePairMap                
                for v in range(numVerts):
                    tupleList = []                    
                    #sort in decent order
                    total = 0
                    lastTotal = 0
                    weightList = []

                    bprint = False
                    blist = []
                    # sort vertex weight and extract bone id ( allows 1 to 3 weight) 
                    for idx in range(len(mesh.weights[v].indices)):

                        if mesh.weights[v].weights[idx] >0.05:
                            weightList.append(  (mesh.weights[v].weights[idx],bidxToSkel[mesh.weights[v].indices[idx]]) )
                            blist.append(bidxToSkel[mesh.weights[v].indices[idx]])
                    weightList.sort(key=itemgetter(1))  

                    for idx in range(len(weightList)):                       
                        byteWeight = weightList[idx][0]
                        lastTotal = total
                        total += byteWeight
                        if idx == len(weightList)-1 and total != 1.0:
                            byteWeight += 1.0 - total
                        tupleList.append((byteWeight, weightList[idx][1]))
                    if len(tupleList) > 3:
                        print (tupleList)
                        print ("ERROR: ", mesh.name, " Vertex " , v ," has more than 3 bone indices!\nSet Vertex Weight Limit (Bone Affect Limit) to 3\n")
                        print ("Aborting...")
                        return 0

                    # build first bone map and bone pair map 
                    # first bone id go to bonemap, 2nd,3rd bone id go to bone pair map as tuples: (1st_bid,2nd_bid) and (1st_bid,3rd_bid)
                    numBone=len(tupleList) 
                    if numBone > 3: numBone =3 
                    for bi in range(numBone):
                        if bi == 0:
                           boneSet.add(tupleList[bi][1])
                        else:
                           bonePairSet.add((tupleList[0][1],tupleList[bi][1]))
                    vertexBoneInfo.append(tupleList)
                #print ("boneSet",boneSet)                 
                #print ("bonePairSet",bonePairSet)

                bonePairMap = []  # mesh bonePairMap contain index into master bonepair table

                bnToIdx = {} # bone id to bonemap idx lookup`
                bpToIdx = {} # bone pair (b1,b[n]) to bonePairMap idx lookup

                boneMap = sorted(boneSet)
                bonePairList = list(bonePairSet)
                #bonePairList.sorted(key=itemgetter(1))

                # create bonemap idx lookup
                for idx, bid in enumerate(boneMap):
                    bnToIdx[bid]=idx
                bmap_size = len(boneMap)
                # construct mesh bonePairMap  and bonepair-to-map_index lookup   
                for bi, bpl in enumerate(bonePairList):
                    bPairFound = False
                    for idx, bp in enumerate(bonePair):
                        if bp == bpl:
                            bonePairMap.append([bpl,idx])                            
                            bPairFound = True
                    if not bPairFound:
                        print ("error, new pair needed",bpl) # don't know how to safely expand bonepair table at this time :X
                        bonePair.append(bpl) # expand bonePair
                        bonePairMap.append([bpl, len(bonePair) - 1 ])
                bonePairMap.sort(key=itemgetter(1))
                for idx, bm in enumerate(bonePairMap):
                    bpToIdx[bm[0][0]*256+bm[0][1]]= bmap_size +idx # for vertex bonepair to mesh bonePairMap index lookup
                    # bonemap and boneParMap are lookup as one array, that is why vertex bonepair index is (bmap_size + bonepairmap_idx)
                                    
                # write mesh header
                bonemap_size = (len(boneMap)+len(bonePairMap))*2 + 2 # material_id take 2 bytes
                bonemap_size_aligned = int((bonemap_size +15)/16) *16 # round up to multiple of 16 bytes                             
              
                #get material_id
                
                f.seek(mesh_start+mtrl_off,NOESEEK_ABS)
                mtrl_id = f.readUShort()
                
                #write new bonemap/bonepair map
                bonemap_start = ms.tell()
                #print("boneMap",boneMap)
                #print("bonePairMap",bonePairMap)
                for bi in boneMap:
                    ms.writeUShort(bi) # write first bone idx
                bonepairmap_start = ms.tell()
                for bi in bonePairMap:
                    ms.writeUShort(bi[1]) # write bonePair idx
                    
                # material_id
                mtrl_start = ms.tell()
                mtrl_name = mesh.matName;
                if mtrl_name.startswith("Mat_"):
                    # This is official game texture
                    ms.writeUShort(mtrl_id)
                else:
                    # Texture not started with Mat_ is a mod texture
                    if mtrl_name in newMtrlList:
                        newMtrlId = numMrtls + newMtrlList.index(mtrl_name)
                    else:      
                        grpID = -1    # assume no custom Mtrl Grp Id
                        name = mesh.name.lower()
                        gs = name.find("grp") # check for custom Mtrl Grp id
                        if gs>=0:
                            ge = name.find("_",gs+3)
                            if ge == -1:
                                grpID =  int(name[gs+3:])                                
                            else:
                                grpID =  int (name[gs+3:ge])
                            print ("custom grp",grpID)
                        newMGrpList.append(grpID)
                        newMtrlList.append(mtrl_name)
                        newMtrlId = numMtrls + len(newMtrlList) - 1
                    ms.writeUShort(newMtrlId)
                pos = ms.tell()                
                for bi in range(int((pos+15)/16)*16 - pos):
                    ms.writeUByte(0)
                    
                he_start = ms.tell()
                # copy last 16 bytes of header
                f.seek(mesh_start + he_off , NOESEEK_ABS)
                ms.writeBytes(f.readBytes(16))
                
                numVerts = len(mesh.positions)              
                vertex_start = ms.tell()
                # write vertex          
                      
                for v in range(numVerts):                
                    start = ms.tell()
                    boneInfo =  vertexBoneInfo[v] # retrieve per vertex weights/indices
                    #print(boneInfo)
                    firstIdx = boneInfo[0][1]
                    #Position
                    mat = invMat[firstIdx]
                    # reverse transform position 
                    vert  = NoeVec4([-mesh.positions[v][0],-mesh.positions[v][1],mesh.positions[v][2],1.0])            
                    newv = mat *  vert
                    ms.writeFloat(newv[0])
                    ms.writeFloat(newv[1])
                    ms.writeFloat(newv[2])
                    #weight
                    for b in range(3):
                        if b > len(boneInfo) -1:
                            ms.writeFloat(0.0)
                        else:
                            ms.writeFloat(boneInfo[b][0])
                    #bonemap Idx
                    for b in range(4):
                        #print(b)
                        if b==0 or b >= len(boneInfo):
                            #unused slot have first bone idx 
                            ms.writeUByte(bnToIdx[boneInfo[0][1]])
                        else:
                            ms.writeUByte(bpToIdx[int(boneInfo[0][1]*256+boneInfo[b][1])])
                    #Normal
                    normv = NoeVec4((-mesh.normals[v][0],-mesh.normals[v][1],mesh.normals[v][2],0.0)) 
                    newn = mat * normv
                    ms.writeFloat(newn[0])
                    ms.writeFloat(newn[1])
                    ms.writeFloat(newn[2]) 
                    
                    #UV
                    ms.writeFloat(mesh.uvs[v][0] % 1.0)
                    ms.writeFloat(mesh.uvs[v][1] % 1.0) 
                    
                fidx_start = ms.tell()-header_start
                # write faces     
                triStrip = triangles_list_to_triangles_strip(mesh)
                num_fidx = len(triStrip)
                for idx in triStrip:
                    ms.writeUInt(idx)  
                print ("triList triStrip len",len(mesh.indices),num_fidx)
                
            else:  # put out a empty mesh which is invisible
                # copy rest of header
                header_cur_pos = ms.tell()
                ms.seek(5*4, NOESEEK_ABS) # mesh is removed, disable any morphs references
                ms.writeUInt(0)
                ms.seek(header_cur_pos,NOESEEK_ABS)
                ms.writeBytes(f.readBytes(header_size - (header_cur_pos-header_start)))
                
                print ("Creating placeholder mesh for Mesh_" + str(i) + "_" + str(m))
                vertex_start = ms.tell()
                numVerts = 3
                for v in range(numVerts):
                    #position
                    for x in range(3):
                        ms.writeFloat(0.0)
                    #bone weights    
                    ms.writeFloat(0)
                    ms.writeFloat(0)
                    ms.writeFloat(0)
                    # bonemap idx
                    ms.writeUByte(0)
                    ms.writeUByte(0)
                    ms.writeUByte(0)
                    ms.writeUByte(0)
                    #normals
                    for x in range(3):
                        ms.writeFloat(0)
                    # UV
                    ms.writeFloat(0)
                    ms.writeFloat(0)
                fidx_start = ms.tell()-header_start
                # face idx  
                num_fidx = 4
                ms.writeUInt(0)
                ms.writeUInt(1)
                ms.writeUInt(2)
                ms.writeUInt(2)
                
            lastpos = ms.tell()
            padding = int((lastpos +15)/16)*16 - lastpos
            for n in range(padding):
                ms.writeByte(0);
            mesh_end = ms.tell()
            # seek back to to mesh header , update all offsets and counts
            ms.seek(header_start)            
            new_mesh_size = mesh_end - header_start 
            ms.writeUInt(new_mesh_size)
            if n_mph == 0 and mesh.name is not "None":
                ms.seek(header_start + 8,NOESEEK_ABS)           
                ms.writeUInt(vertex_start - header_start) # header size
                ms.seek(header_start + 4 * 7, NOESEEK_ABS)
                ms.writeUInt(len(boneMap))
                ms.writeUInt(bonemap_start-header_start)
                ms.writeUInt(len(bonePairMap))
                ms.writeUInt(bonepairmap_start-header_start)
                ms.seek(header_start + 4 * 14, NOESEEK_ABS)
                ms.writeUInt(mtrl_start-header_start)    # material index pos
                ms.writeUInt(he_start-header_start)      # offset of last 16 bytes of header
                ms.writeUInt(vertex_start-header_start)  # vertex offset
            #update vertex cnt/face_idx cnt/face_idx offset    
            ms.seek(header_start + 4 * 4, NOESEEK_ABS)
            ms.writeUInt(num_fidx)
            ms.seek(header_start + 4 * 17, NOESEEK_ABS)
            ms.writeUInt(numVerts)
            ms.writeUInt(fidx_start)   
            ms.writeUInt(num_fidx)

            # move to next mesh header
            f.seek(mesh_start + mesh_size, NOESEEK_ABS)
    
    # writing out new bonepair amature
    new_bonepair_cnt = len(bonePair)

    for bp in bonePair:
        bs.writeByte(bp[0])
        bs.writeByte(bp[1])      
    # pad to 16 byte aligned
    pad = bs.tell() % 0x10
    if pad  > 0:
        for i in range((0x10-pad)):
            bs.writeByte(0) 
    new_bp_matrix_offs = bs.tell()

    # copy orignal bonepair matrix
    f.seek(offsetMeshStart + offsetBones2, NOESEEK_ABS)
    bs.writeBytes(f.readBytes(numBones2 * 0x40) )

    # generate new bonepair matrices for new pairs
    for i in range(new_bonepair_cnt - numBones2):
        parent_inv_matrix = invMat[bonePair[numBones2 + i][0]]
        local_matrix = boneMat[bonePair[numBones2 + i][1]]
        #get parent to child transform
        parent_to_local = parent_inv_matrix * local_matrix
        # bonepair matrix is the inverse transform matrix from child to parent
        bp_mat = parent_to_local.inverse()
        bs.writeFloat(bp_mat[0][0]);bs.writeFloat(bp_mat[0][1]);bs.writeFloat(bp_mat[0][2]);bs.writeFloat(bp_mat[0][3])
        bs.writeFloat(bp_mat[1][0]);bs.writeFloat(bp_mat[1][1]);bs.writeFloat(bp_mat[1][2]);bs.writeFloat(bp_mat[1][3])
        bs.writeFloat(bp_mat[2][0]);bs.writeFloat(bp_mat[2][1]);bs.writeFloat(bp_mat[2][2]);bs.writeFloat(bp_mat[2][3])        
        bs.writeFloat(bp_mat[3][0]);bs.writeFloat(bp_mat[3][1]);bs.writeFloat(bp_mat[3][2]);bs.writeFloat(bp_mat[3][3])

    new_tex_offs = bs.tell()
    # copy original texture entry
    bs.writeBytes(f.readBytes(numTextures *4))  # each texture take one UInt slot
    newTexList = []
    newMtrlIDList = []
    # find out how many unqiue new texture/images is needed
    for i,mtrl in enumerate(newMtrlList):
        for m in mdl.modelMats.matList:
            if m.name == mtrl:
                mtrlObj = m
                break        
        if mtrlObj.texName not in newTexList:
            newTexList.append(mtrlObj.texName)
            texId = numTextures + len(newTexList) - 1
            # write new texture entry
            bs.writeUInt(texId)
        else:
            texId = numTextures + newTexList.index(mtrlObj.texName) 
        newMtrlIDList.append((texId,newMGrpList[i]))  # material has (TextureID, MGroupID)
    new_texture_cnt = numTextures + len(newTexList)

    while bs.tell() % 16 != 0: # 16 byte aligned
        bs.writeByte(0);         
        
    new_material_offs = bs.tell()
    new_material_cnt = numMtrls + len(newMtrlList)  
    f.seek( offsetMeshStart + offsetMrtl, NOESEEK_ABS)
    # copy original materails
    first_mtrl_tex,first_mtrl_flags = (f.readUInt(),f.readUInt())
    bs.writeUInt(first_mtrl_tex)
    bs.writeUInt(first_mtrl_flags)
    bs.writeBytes(f.readBytes((numMtrls-1) * 8)) # each material takes 8 bytes (texId and flags)
    # write new materails
    for texID,MGrpID in newMtrlIDList:
        bs.writeUInt(texID)
        if MGrpID == -1 :      # Mtrl group not defined      
            bs.writeUInt(first_mtrl_flags) # use 1st material flags
        else:
            bs.writeUInt(MGrpID) 
    while bs.tell() % 16 != 0: # 16 byte aligned
        bs.writeByte(0);         
    
    new_baseVert_offs  = bs.tell()   
    
    f.seek( offsetMeshStart +  offsetBaseVert, NOESEEK_ABS)
    # copy original base shape and blendshapes 
    bs.writeBytes(f.readBytes(offsetMeshes-offsetBaseVert))
    
    new_meshes_start =  bs.tell()
    
    # write all meshes
    last_grp = 0
    for group,ms in meshBufList:
        if group != last_grp:
            mesh2_start = bs.tell()
            last_grp = group
        bs.writeBytes(ms.getBuffer())

    numNewTex = len (newTexList)    
    if num_images > 0 or numNewTex > 0:     
        f.seek(offset_image , NOESEEK_ABS)
        image_start = f.tell()
        new_image_start = bs.tell()
        print ("tex start",hex(image_start))
        # copy image list header and set number of images 
        if num_images == 0: # build a image list header if there was'nt one before 
           bs.writeUInt(0xffffffff); bs.writeUint(0)
           bs.writeUInt(0x00000020); bs.writeUInt(0x00440200);
           bs.writeUInt(0); bs.writeUInt(numNewTex);
           bs.writeUInt(0);bs.writeUInt(0)
        else:  # copy and update existing image list header and copy original images
           bs.writeBytes(f.readBytes(0x14))
           f.readUInt() 
           bs.writeUInt(num_images + numNewTex)
           bs.writeBytes(f.readBytes(0x08))
           # copy original textures
           bs.writeBytes(f.readBytes(len(newMesh)-f.tell()))
        # write out new Images
        for texName in newTexList:
            texture = rapi.loadExternalTex(texName)                   
            writeImage(bs,texture)
            
        # update num of image and image start offset
        bs.seek(0x08, NOESEEK_ABS)  
        bs.writeUInt( num_images + numNewTex )
        bs.writeUInt(new_image_start) # this show up twice
        bs.writeUInt(new_image_start)
    
    # new tri-list is bigger than original. refresh mesh list starting offset
    bs.seek(meshes2_offset_pos, NOESEEK_ABS)
    bs.writeUInt(mesh2_start-offsetMeshStart) 
    
    inc_size = (new_baseVert_offs - offsetMeshStart - offsetBaseVert)
    # update model header with new offset
    # new bone_pair/texture/material shift all the section offset come after it
    if inc_size >  0:
        bs.seek(numBones2_pos,NOESEEK_ABS)
        bs.writeUInt(new_bonepair_cnt)
        bs.seek(4, NOESEEK_REL)
        bs.writeUInt(new_bp_matrix_offs-offsetMeshStart)
        bs.seek(4, NOESEEK_REL)
        bs.writeUInt(new_meshes_start-offsetMeshStart)
        bs.seek(4, NOESEEK_REL)
        bs.writeUInt(mesh2_start-offsetMeshStart)
        bs.writeUInt(new_texture_cnt)
        bs.writeUInt(new_tex_offs-offsetMeshStart)        
        bs.writeUInt(new_material_cnt)
        bs.writeUInt(new_material_offs-offsetMeshStart)
        bs.seek(8, NOESEEK_REL)
        bs.writeUInt(offsetBaseVert + inc_size)        
        bs.seek(4, NOESEEK_REL)
        bs.writeUInt(offsetBlendData + inc_size)        
        bs.seek(4, NOESEEK_REL)
        bs.writeUInt(offsetUnk1 + inc_size)
        bs.writeUInt(offsetUnk2 + inc_size)
        bs.writeUInt(offsetUnk3 + inc_size)
        # all blendshape data offset need to be adjusted
        f.seek(offsetBlendData + offsetMeshStart,NOESEEK_ABS)
        bs.seek((offsetBlendData + offsetMeshStart + inc_size),NOESEEK_ABS)
        for i in range(numBlendData):
            bs.writeUInt(f.readUInt()) # vtx count unchanged
            o = f.readUInt()
            bs.writeUInt(o+inc_size) # offset of delta section changed
    return 1 