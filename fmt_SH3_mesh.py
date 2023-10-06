#
# Silent Hill 3 PC Model loader
# alanm1
# v0.1
#
#Based on:
#Tomb Raider: Underworld/Lara Croft and The Guardian Of Light [PC/X360] - ".tr8mesh" Loader
#By Gh0stblade
#v2.4
#Special thanks: Chrrox
#Options: These are bools that enable/disable certain features! 
#Var                            Effect
#Misc
#Mesh Global
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
    
def registerNoesisTypes():
    handle = noesis.register("Silent Hill 3: 3D Mesh [PC]", ".dat")
    noesis.setHandlerTypeCheck(handle, meshCheckType)
    noesis.setHandlerLoadModel(handle, meshLoadModel)

    handle = noesis.register("Silent Hill 3: 3D Mesh [PC]", ".tps")
    noesis.setHandlerTypeCheck(handle, meshCheckType)
    noesis.setHandlerLoadModel(handle, meshLoadModel)
    
    handle = noesis.register("Silent Hill 3: 2D Texture [PC]", ".dc5")
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
		print("Fatal Error: Unknown file magic: " + str(hex(magic) + " expected PCD9!"))
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
        # main meshes           
        self.loadMeshes(bs,0,self.numMeshes,self.offsetMeshes)
        # tansparent hair meshes
        self.loadMeshes(bs,1,self.numMeshes2,self.offsetMeshes2)
        
    def loadMeshes(self, bs, meshGroup, numMeshes, offsetMeshes):
        cur_pos = self.offsetMeshStart + offsetMeshes;        
        for i in range(numMeshes):        
            bs.seek(cur_pos, NOESEEK_ABS)
            mesh_size = bs.readUInt()
            unk =  bs.readUInt()
            header_size = bs.readUInt()
            bs.seek(4*4, NOESEEK_REL)
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
            for b in range(num_bones2):
                bonepair_idx = bs.readUShort()                
                # take the 2nd bone_id of the pair.
                self.boneMap.append(self.bonePair[bonepair_idx][1])
            
            rapi.rpgSetBoneMap(self.boneMap)
            
            bs.seek (cur_pos + mat_id_offset, NOESEEK_ABS)
            mat_id = bs.readUShort()
                        
            # set up material
            self.setMaterial(mat_id)
            
            # advance to the vertex buffer
            bs.seek(cur_pos + header_size, NOESEEK_ABS)
                        
            if debug:
                print("Mesh Info Start: " + str(bs.tell()))
                print ("Bonemap ",i,self.boneMap)
            meshFile.buildMesh(self, [num_vertex, cur_pos + fidx_offset, numFidx, meshGroup], i, self.boneMap, self.offsetBones, self.offsetFaceIdx, self.numBones)
            if debug:
                print("Mesh Info End: " + str(bs.tell()))
            cur_pos = cur_pos + mesh_size
            
    def buildMesh(self, meshInfo, meshIndex, boneMap, uiOffsetBoneMap, uiOffsetFaceData, usNumBones):        
        
        bs = self.inFile        
        
        rapi.rpgSetName("Mesh_"+ str(meshInfo[3]) + "_" + str(meshIndex))
        rapi.rpgSetPosScaleBias((fDefaultMeshScale, fDefaultMeshScale, fDefaultMeshScale), (0, 0, 0))
        

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
        rapi.rpgSetTransform(NoeMat43((NoeVec3((1, 0, 0)), NoeVec3((0, -1, 0)), NoeVec3((0, 0, 1)), NoeVec3((0, 0, 0)))))
        

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
            
                Bi4 = 255   #if bone weight is 0.0, set bone id to 255(dummy). prevent weight export problem
                if Bw3 == 0.0:
                    Bi3 = 255
                    if Bw2 == 0.0:
                        Bi2 = 255            
                biList.append(Bi1)
                biList.append(Bi2)
                biList.append(Bi3)
                biList.append(Bi4)

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
            rapi.rpgBindBoneIndexBufferOfs(biBuff, noesis.RPGEODATA_UBYTE, 4, 0, 0x4)                    
            rapi.rpgBindBoneWeightBufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshBwPos, 0x4)


        rapi.rpgBindUV1BufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshUV1Pos)
            
        rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_UINT, meshInfo[2], noesis.RPGEO_TRIANGLE_STRIP, 0x1)
        if bOptimizeMesh:
            rapi.rpgOptimize()
        rapi.rpgClearBufferBinds()
                          
                      

            
    def buildSkeleton(self):
        bs = self.inFile
        
        BonePID = []
        if self.numBones > 0:
            bs.seek(self.offsetSkel + self.offsetMeshStart, NOESEEK_ABS)
            for i in range(self.numBones):
                BonePID.append(bs.readByte())

            bs.seek(self.offsetBones + self.offsetMeshStart, NOESEEK_ABS)
            for i in range(self.numBones):           
                # read mesh initial matrix                
                mat = NoeMat44([[bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()]])
                self.boneMat.append(mat)
                
                quat = NoeQuat([0, 0, 0, 1])
                bone_mat = quat.toMat43()                
                
                bone_mat[0]=[mat[0][0],mat[0][1],mat[0][2] ]
                bone_mat[1]=[mat[1][0],mat[1][1],mat[1][2] ]
                bone_mat[2]=[mat[2][0],mat[2][1],mat[2][2] ]
                bone_mat[3]=[mat[3][0],-mat[3][1],mat[3][2] ]
                
                self.boneList.append(NoeBone(i, "bone%03i"%i, bone_mat, None, BonePID[i]))
   
        
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
    return 1
