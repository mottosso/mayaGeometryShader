import ctypes
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

from maya import cmds

drawAgent = None
effect = None


def drawCallback(context, data):
    """Called per frame to do the actual drawing"""

    footData = data

    if not isinstance(footData, DrawOverrideData):
        return

    multiplier = footData.fMultiplier
    color = [footData.fColor[0], footData.fColor[1], footData.fColor[2], 1.0]

    global drawAgent
    if drawAgent is None:
        if omr.MRenderer.drawAPIIsOpenGL():
            drawAgent = DrawAgent()

    if drawAgent is not None:
        drawAgent.beginDraw(context, color, multiplier)
        drawAgent.drawBoundingBox(context)
        drawAgent.endDraw(context)


def install():
    cmds.loadPlugin(__file__)
    return DrawOverrideNode


def uninstall():
    cmds.unloadPlugin(__name__)


def reinstall():
    scene = cmds.file(sceneName=True, query=True)
    cmds.file(new=True, force=True)

    try:
        uninstall()
        install()
    finally:

        if scene:
            cmds.file(scene, open=True, force=True)


class DrawOverrideNode(omui.MPxLocatorNode):
    """Just a node to carry the DrawOverride below"""

    id = om.MTypeId(0x80008)
    drawDbClassification = "drawdb/geometry/DrawOverrideNode"
    drawRegistrantId = "DrawOverrideNodePlugin"

    size = None  # The size of the foot

    @classmethod
    def creator(cls):
        return cls()

    @classmethod
    def initialize(cls):
        unitFn = om.MFnUnitAttribute()

        cls.size = unitFn.create("size", "sz", om.MFnUnitAttribute.kDistance)
        unitFn.default = om.MDistance(1.0)
        unitFn.keyable = True
        unitFn.storable = True
        unitFn.writable = True

        om.MPxNode.addAttribute(cls.size)

    def __init__(self):
        omui.MPxLocatorNode.__init__(self)

    def compute(self, plug, data):
        return None


class DrawOverrideData(om.MUserData):
    def __init__(self):
        om.MUserData.__init__(self, False)  # Don't delete after draw

        self.fMultiplier = 0.0
        self.fColor = [0.0, 0.0, 0.0]
        self.fDrawOV = om.MDAGDrawOverrideInfo()


class DrawAgent(object):
    def __init__(self):
        self.mShader = None
        self.mBoundingboxVertexBuffer = None
        self.mBoundingboxIndexBuffer = None

    def __del__(self):
        if self.mShader is not None:
            shaderMgr = omr.MRenderer.getShaderManager()
            if shaderMgr is not None:
                shaderMgr.releaseShader(self.mShader)
            self.mShader = None

        self.mBoundingboxVertexBuffer = None
        self.mBoundingboxIndexBuffer = None

    def beginDraw(self, context, color, scale):
        self.initShader()
        self.initBuffers()

        if self.mShader is not None:
            self.mShader.bind(context)
            self.mShader.setParameter("scale", scale)
            self.mShader.activatePass(context, 0)

    def drawBoundingBox(self, context):
        drawBoundingBox = (
            self.mBoundingboxVertexBuffer is not None and
            self.mBoundingboxIndexBuffer is not None
        )

        if drawBoundingBox:
            omr.MRenderUtilities.drawSimpleMesh(context,
                                                self.mBoundingboxVertexBuffer,
                                                self.mBoundingboxIndexBuffer,
                                                # omr.MGeometry.kPoints,
                                                # omr.MGeometry.kLines,
                                                # omr.MGeometry.kTriangles,
                                                omr.MGeometry.kTriangleStrip,
                                                0, 3 * 12)

    def endDraw(self, context):
        if self.mShader is not None:
            self.mShader.unbind(context)

    def initShader(self):
        global effect

        if self.mShader is None or effect:

            if effect is None:
                return False

            print("Recreating shader..")
            shaderMgr = omr.MRenderer.getShaderManager()
            if shaderMgr is not None:
                self.mShader = shaderMgr.getEffectsFileShader(
                    effect, "", useEffectCache=False
                )

            effect = None

        return self.mShader is not None

    def initBuffers(self):
        global soleCount, sole
        global heelCount, heel

        if self.mBoundingboxVertexBuffer is None:
            count = 8
            rawData = [[-0.5, -0.5, -0.5],
                       [0.5, -0.5, -0.5],
                       [0.5, -0.5, 0.5],
                       [-0.5, -0.5, 0.5],
                       [-0.5, 0.5, -0.5],
                       [0.5, 0.5, -0.5],
                       [0.5, 0.5, 0.5],
                       [-0.5, 0.5, 0.5]]

            desc = omr.MVertexBufferDescriptor(
                "", omr.MGeometry.kPosition, omr.MGeometry.kFloat, 3
            )

            self.mBoundingboxVertexBuffer = omr.MVertexBuffer(desc)

            dataAddress = self.mBoundingboxVertexBuffer.acquire(count, True)
            data = ((ctypes.c_float * 3) * count).from_address(dataAddress)

            for i in range(count):
                data[i][0] = rawData[i][0]
                data[i][1] = rawData[i][1]
                data[i][2] = rawData[i][2]

            self.mBoundingboxVertexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mBoundingboxIndexBuffer is None:
            count = 24
            rawData = [0, 1, 1, 2, 2, 3, 3, 0, 4, 5, 5, 6, 6, 7, 7,
                       4, 0, 4, 1, 5, 2, 6, 3, 7]

            self.mBoundingboxIndexBuffer = omr.MIndexBuffer(
                omr.MGeometry.kUnsignedInt32)

            dataAddress = self.mBoundingboxIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint * count).from_address(dataAddress)

            for i in range(count):
                data[i] = rawData[i]

            self.mBoundingboxIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        return True


class DrawOverrideDrawOverride(omr.MPxDrawOverride):
    @classmethod
    def creator(cls, obj):
        return cls(obj)

    def __init__(self, obj):
        super(DrawOverrideDrawOverride, self).__init__(obj, drawCallback)
        self.mCustomBoxDraw = True
        self.mCurrentBoundingBox = om.MBoundingBox()

    def supportedDrawAPIs(self):
        return omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile

    def isBounded(self, objPath, cameraPath):
        return True

    def boundingBox(self, objPath, cameraPath):
        corner1 = om.MPoint(-0.5, 0.5, -0.5)
        corner2 = om.MPoint(0.5, 0.5, 0.5)

        multiplier = self.getMultiplier(objPath)
        corner1 *= multiplier
        corner2 *= multiplier

        self.mCurrentBoundingBox.clear()
        self.mCurrentBoundingBox.expand(corner1)
        self.mCurrentBoundingBox.expand(corner2)

        return self.mCurrentBoundingBox

    def disableInternalBoundingBoxDraw(self):
        return True

    def getMultiplier(self, objPath):
        node = objPath.node()
        plug = om.MPlug(node, DrawOverrideNode.size)

        if not plug.isNull:
            sizeVal = plug.asMDistance()

        return sizeVal.asCentimeters()

    def prepareForDraw(self, objPath, cameraPath, frameContext, oldData):
        data = oldData
        if not isinstance(data, DrawOverrideData):
            data = DrawOverrideData()

        data.fMultiplier = self.getMultiplier(objPath)
        color = omr.MGeometryUtilities.wireframeColor(objPath)
        data.fColor = [color.r, color.g, color.b]

        return data


def initializePlugin2(obj):

    # Register the imported Python module, rather than
    # read the file as plain-text which is the norm.

    this = __import__("pyDrawOverride")
    DrawOverrideNode = this.DrawOverrideNode
    DrawOverrideDrawOverride = this.DrawOverrideDrawOverride

    plugin = om.MFnPlugin(obj, "Autodesk", "3.0", "Any")
    plugin.registerNode("DrawOverrideNode",
                        DrawOverrideNode.id,
                        DrawOverrideNode.creator,
                        DrawOverrideNode.initialize,
                        om.MPxNode.kLocatorNode,
                        DrawOverrideNode.drawDbClassification)

    omr.MDrawRegistry.registerDrawOverrideCreator(
        DrawOverrideNode.drawDbClassification,
        DrawOverrideNode.drawRegistrantId,
        DrawOverrideDrawOverride.creator
    )


def uninitializePlugin2(obj):
    plugin = om.MFnPlugin(obj)
    plugin.deregisterNode(DrawOverrideNode.id)

    omr.MDrawRegistry.deregisterDrawOverrideCreator(
        DrawOverrideNode.drawDbClassification,
        DrawOverrideNode.drawRegistrantId
    )
