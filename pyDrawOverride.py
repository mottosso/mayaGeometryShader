import os
import ctypes
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

from maya import cmds

# Plug-in aren't imported like normal Python modules,
# but rather read as plain-text. This compensates for that.
__file__ = cmds.pluginInfo("pyGeometryOverride", path=True, query=True)

drawAgent = None


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


class DrawOverrideNode(omui.MPxLocatorNode):
    id = om.MTypeId(0x80008)
    drawDbClassification = "drawdb/geometry/DrawOverrideNode"
    drawRegistrantId = "DrawOverrideNodePlugin"

    @staticmethod
    def creator():
        return DrawOverrideNode()

    @staticmethod
    def initialize():
        pass

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
                                                omr.MGeometry.kLines,
                                                0, 24)

    def endDraw(self, context):
        if self.mShader is not None:
            self.mShader.unbind(context)

    def initShader(self):
        if self.mShader is None:
            shaderMgr = omr.MRenderer.getShaderManager()
            if shaderMgr is not None:
                dirname = os.path.dirname(__file__)
                fname = os.path.join(dirname, "noGeometryShader.ogsfx")
                self.mShader = shaderMgr.getEffectsFileShader(
                    fname, "", useEffectCache=False
                )

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
        corner1 = om.MPoint(-0.17, 0.0, -0.7)
        corner2 = om.MPoint(0.17, 0.0, 0.3)

        multiplier = 1
        corner1 *= multiplier
        corner2 *= multiplier

        self.mCurrentBoundingBox.clear()
        self.mCurrentBoundingBox.expand(corner1)
        self.mCurrentBoundingBox.expand(corner2)

        return self.mCurrentBoundingBox

    def disableInternalBoundingBoxDraw(self):
        return True

    def prepareForDraw(self, objPath, cameraPath, frameContext, oldData):
        data = oldData
        if not isinstance(data, DrawOverrideData):
            data = DrawOverrideData()

        data.fMultiplier = 1
        color = omr.MGeometryUtilities.wireframeColor(objPath)
        data.fColor = [color.r, color.g, color.b]

        return data


def initializePlugin2(obj):
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