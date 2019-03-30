import ctypes
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr


# Globals
blendState = None
rasterState = None
drawAgent = None


def drawCallback(context, data):
    footData = data

    if not isinstance(footData, footPrintData):
        return

    multiplier = footData.fMultiplier
    color = [footData.fColor[0], footData.fColor[1], footData.fColor[2], 1.0]

    stateMgr = context.getStateManager()
    oldBlendState = None
    oldRasterState = None
    rasterStateModified = False

    global drawAgent
    if drawAgent is None:
        if omr.MRenderer.drawAPIIsOpenGL():
            drawAgent = footPrintDrawAgentGL()

    if drawAgent is not None:
        drawAgent.beginDraw(context, color, multiplier)
        # drawAgent.drawShaded(context)
        drawAgent.drawBoundingBox(context)
        drawAgent.endDraw(context)

    # Restore old blend state and old raster state
    if stateMgr is not None:
        if oldBlendState is not None:
            stateMgr.setBlendState(oldBlendState)

        if rasterStateModified and oldRasterState is not None:
            stateMgr.setRasterizerState(oldRasterState)


# Foot Data
sole = [
    [0.00, 0.0, -0.70],
    [0.04, 0.0, -0.69],
    [0.09, 0.0, -0.65],
    [0.13, 0.0, -0.61],
    [0.16, 0.0, -0.54],
    [0.17, 0.0, -0.46],
    [0.17, 0.0, -0.35],
    [0.16, 0.0, -0.25],
    [0.15, 0.0, -0.14],
    [0.13, 0.0, 0.00],
    [0.00, 0.0, 0.00],
    [-0.13, 0.0, 0.00],
    [-0.15, 0.0, -0.14],
    [-0.16, 0.0, -0.25],
    [-0.17, 0.0, -0.35],
    [-0.17, 0.0, -0.46],
    [-0.16, 0.0, -0.54],
    [-0.13, 0.0, -0.61],
    [-0.09, 0.0, -0.65],
    [-0.04, 0.0, -0.69],
    [-0.00, 0.0, -0.70]
]

heel = [
    [0.00, 0.0, 0.06],
    [0.13, 0.0, 0.06],
    [0.14, 0.0, 0.15],
    [0.14, 0.0, 0.21],
    [0.13, 0.0, 0.25],
    [0.11, 0.0, 0.28],
    [0.09, 0.0, 0.29],
    [0.04, 0.0, 0.30],
    [0.00, 0.0, 0.30],
    [-0.04, 0.0, 0.30],
    [-0.09, 0.0, 0.29],
    [-0.11, 0.0, 0.28],
    [-0.13, 0.0, 0.25],
    [-0.14, 0.0, 0.21],
    [-0.14, 0.0, 0.15],
    [-0.13, 0.0, 0.06],
    [-0.00, 0.0, 0.06]
]

soleCount = len(sole)
heelCount = len(heel)


class footPrint(omui.MPxLocatorNode):
    id = om.MTypeId(0x80007)
    drawDbClassification = "drawdb/geometry/footPrint"
    drawRegistrantId = "FootprintNodePlugin"

    @staticmethod
    def creator():
        return footPrint()

    @staticmethod
    def initialize():
        pass

    def __init__(self):
        omui.MPxLocatorNode.__init__(self)

    def compute(self, plug, data):
        return None


class footPrintData(om.MUserData):
    def __init__(self):
        om.MUserData.__init__(self, False)  # don't delete after draw

        self.fMultiplier = 0.0
        self.fColor = [0.0, 0.0, 0.0]
        self.fCustomBoxDraw = False
        self.fDrawOV = om.MDAGDrawOverrideInfo()


class footPrintDrawAgent:
    def __init__(self):
        self.mShader = None

        self.mBoundingboxVertexBuffer = None
        self.mBoundingboxIndexBuffer = None
        self.mSoleVertexBuffer = None
        self.mHeelVertexBuffer = None
        self.mSoleWireIndexBuffer = None
        self.mHeelWireIndexBuffer = None
        self.mSoleShadedIndexBuffer = None
        self.mHeelShadedIndexBuffer = None

    def __del__(self):
        if self.mShader is not None:
            shaderMgr = omr.MRenderer.getShaderManager()
            if shaderMgr is not None:
                shaderMgr.releaseShader(self.mShader)
            self.mShader = None

        self.mBoundingboxVertexBuffer = None
        self.mBoundingboxIndexBuffer = None
        self.mSoleVertexBuffer = None
        self.mHeelVertexBuffer = None
        self.mSoleWireIndexBuffer = None
        self.mHeelWireIndexBuffer = None
        self.mSoleShadedIndexBuffer = None
        self.mHeelShadedIndexBuffer = None

    def beginDraw(self, context, color, scale):
        self.initShader()
        self.initBuffers()

        if self.mShader is not None:
            self.mShader.setParameter("matColor", color)
            self.mShader.bind(context)
            self.mShader.activatePass(context, 0)

    def drawShaded(self, context):
        global soleCount, heelCount

        # Draw the sole
        drawSole = (
            self.mSoleVertexBuffer is not None and
            self.mSoleShadedIndexBuffer is not None
        )

        drawHeel = (
            self.mHeelVertexBuffer is not None and
            self.mHeelShadedIndexBuffer is not None
        )

        if drawSole:
            omr.MRenderUtilities.drawSimpleMesh(context,
                                                self.mSoleVertexBuffer,
                                                self.mSoleShadedIndexBuffer,
                                                omr.MGeometry.kTriangles,
                                                0, 3 * (soleCount - 2))

        # Draw the heel
        if drawHeel:
            omr.MRenderUtilities.drawSimpleMesh(context,
                                                self.mHeelVertexBuffer,
                                                self.mHeelShadedIndexBuffer,
                                                omr.MGeometry.kTriangles,
                                                0, 3 * (heelCount - 2))

    def drawBoundingBox(self, context):
        drawBoundingBox = (
            self.mBoundingboxVertexBuffer is not None and
            self.mBoundingboxIndexBuffer is not None
        )

        if drawBoundingBox:
            omr.MRenderUtilities.drawSimpleMesh(context,
                                                self.mBoundingboxVertexBuffer,
                                                self.mBoundingboxIndexBuffer,
                                                omr.MGeometry.kPoints,
                                                0, 24)

    def endDraw(self, context):
        if self.mShader is not None:
            self.mShader.unbind(context)

    def initShader(self):
        if self.mShader is None:
            shaderMgr = omr.MRenderer.getShaderManager()
            if shaderMgr is not None:
                shaderCode = self.getGeometryShaderCode()
                shaderCode = self.getShaderCode()
                self.mShader = shaderMgr.getEffectsBufferShader(
                    shaderCode, len(shaderCode), ""
                )

        return self.mShader is not None

    def shaderCode(self):
        return ""

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

        if self.mSoleVertexBuffer is None:
            desc = omr.MVertexBufferDescriptor(
                "", omr.MGeometry.kPosition,
                omr.MGeometry.kFloat, 3
            )

            self.mSoleVertexBuffer = omr.MVertexBuffer(desc)

            dataAddress = self.mSoleVertexBuffer.acquire(soleCount, True)
            data = ((ctypes.c_float * 3) * soleCount).from_address(dataAddress)

            for i in range(soleCount):
                data[i][0] = sole[i][0]
                data[i][1] = sole[i][1]
                data[i][2] = sole[i][2]

            self.mSoleVertexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mHeelVertexBuffer is None:
            self.mHeelVertexBuffer = omr.MVertexBuffer(
                omr.MVertexBufferDescriptor(
                    "", omr.MGeometry.kPosition,
                    omr.MGeometry.kFloat, 3
                ))

            dataAddress = self.mHeelVertexBuffer.acquire(heelCount, True)
            data = ((ctypes.c_float * 3) * heelCount).from_address(dataAddress)

            for i in range(heelCount):
                data[i][0] = heel[i][0]
                data[i][1] = heel[i][1]
                data[i][2] = heel[i][2]

            self.mHeelVertexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        # if self.mSoleWireIndexBuffer is None:
        #     count = 2 * (soleCount - 1)
        #     rawData = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8,
        #                9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15,
        #                16, 16, 17, 17, 18, 18, 19, 19, 20]

        #     self.mSoleWireIndexBuffer = omr.MIndexBuffer(
        #         omr.MGeometry.kUnsignedInt32)

        #     dataAddress = self.mSoleWireIndexBuffer.acquire(count, True)
        #     data = (ctypes.c_uint * count).from_address(dataAddress)

        #     for i in range(count):
        #         data[i] = rawData[i]

        #     self.mSoleWireIndexBuffer.commit(dataAddress)
        #     dataAddress = None
        #     data = None

        # if self.mHeelWireIndexBuffer is None:
        #     count = 2 * (heelCount - 1)
        #     rawData = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9,
        #                10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16]

        #     self.mHeelWireIndexBuffer = omr.MIndexBuffer(
        #         omr.MGeometry.kUnsignedInt32)

        #     dataAddress = self.mHeelWireIndexBuffer.acquire(count, True)
        #     data = (ctypes.c_uint * count).from_address(dataAddress)

        #     for i in range(count):
        #         data[i] = rawData[i]

        #     self.mHeelWireIndexBuffer.commit(dataAddress)
        #     dataAddress = None
        #     data = None

        if self.mSoleShadedIndexBuffer is None:
            count = 3 * (soleCount - 2)
            rawData = [0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 5, 0, 5, 6, 0,
                       6, 7, 0, 7, 8, 0, 8, 9, 0, 9, 10, 0, 10, 11, 0,
                       11, 12, 0, 12, 13, 0, 13, 14, 0, 14, 15, 0, 15,
                       16, 0, 16, 17, 0, 17, 18, 0, 18, 19, 0, 19, 20]

            self.mSoleShadedIndexBuffer = omr.MIndexBuffer(
                omr.MGeometry.kUnsignedInt32)

            dataAddress = self.mSoleShadedIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint * count).from_address(dataAddress)

            for i in range(count):
                data[i] = rawData[i]

            self.mSoleShadedIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        if self.mHeelShadedIndexBuffer is None:
            count = 3 * (heelCount - 2)
            rawData = [0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 5, 0, 5, 6, 0, 6,
                       7, 0, 7, 8, 0, 8, 9, 0, 9, 10, 0, 10, 11, 0, 11,
                       12, 0, 12, 13, 0, 13, 14, 0, 14, 15, 0, 15, 16]

            self.mHeelShadedIndexBuffer = omr.MIndexBuffer(
                omr.MGeometry.kUnsignedInt32)

            dataAddress = self.mHeelShadedIndexBuffer.acquire(count, True)
            data = (ctypes.c_uint * count).from_address(dataAddress)

            for i in range(count):
                data[i] = rawData[i]

            self.mHeelShadedIndexBuffer.commit(dataAddress)
            dataAddress = None
            data = None

        return True


class footPrintDrawAgentGL(footPrintDrawAgent):
    def __init__(self):
        footPrintDrawAgent.__init__(self)

    def getShaderCode(self):
        shaderCode = """
#version 410

uniform mat4 gWVPXf : WorldViewProjection;
uniform mat4 world : World;
uniform mat4 gWVXf : WorldView;
uniform mat4 gPXf : Projection;
uniform float4 matColor = {0.8, 0.2, 0.0, 1.0};
uniform float scale = 1.0;

attribute VS_INPUT {
    vec3 inPosition : POSITION;
    vec2 inUVset0 : TEXCOORD0;
    vec3 inNormal : NORMAL;
};

attribute VS_TO_PS {
    vec3 vsPosition : POSITION;
    vec4 vsUVset0 : TEXCOORD0;
    vec3 vsNormal : NORMAL;
};

uniform vec4 diffuseColor = { 0.5, 0.0, 0.5, 1.0 };


GLSLShader ShaderVertex {
    void main() {
        vs_output.vsNormal = (world * vec4(inNormal, 1.0)).xyz;
        vs_output.vsUVset0 = vec4(inUVset0.x, 1.0f - inUVset0.y, 0, 0);
        gl_Position = gWVPXf*vec4(inPosition, 1.0);
    }
}

GLSLShader ShaderGeometry
{
    layout(triangles_adjacency) in;
    layout(triangle_strip, max_vertices = 15) out;

    void main()
    {
    }
}

attribute pixel_output {
    vec4 colorOut : COLOR0;
};

GLSLShader ShaderPixel {
    void main() {
        colorOut = vec4(px_input.vsNormal.xyz, 1.0);
    }
}

technique Main {
    pass P0 {
        VertexShader (in VS_INPUT, out VS_TO_PS vs_output) = ShaderVertex;
        PixelShader (in VS_TO_PS px_input, out pixel_output) = ShaderPixel;
    }
}
"""
        return shaderCode

    def getGeometryShaderCode(self):
        shaderCode = """
#version 410

uniform mat4 gWVPXf : WorldViewProjection;
uniform mat4 world : World;
uniform mat4 gWVXf : WorldView;
uniform mat4 gPXf : Projection;
uniform float4 matColor = {0.8, 0.2, 0.0, 1.0};
uniform float scale = 1.0;

attribute VS_INPUT {
    vec3 inPosition : POSITION;
    vec2 inUVset0 : TEXCOORD0;
    vec3 inNormal : NORMAL;
};

attribute VS_TO_GEO {
    vec3 vNormal : NORMAL;
};

attribute GEO_TO_PS {
    vec4 gColor;
}

attribute PS_OUT {
    vec4 colorOut : COLOR0;
};

uniform vec4 diffuseColor = { 0.5, 0.0, 0.5, 1.0 };

GLSLShader ShaderVertex {
    void main() {
        geo_out.vNormal = (world * vec4(inNormal, 1.0)).xyz;
        gl_Position = gWVPXf*vec4(inPosition, 1.0);
    }
}

GLSLShader ShaderGeometry
{
    layout(triangles_adjacency) in;
    layout(triangle_strip, max_vertices = 15) out;

    void main()
    {
        // Output center face:
        geo_out.gColor = diffuseColor;
        gl_Position = gl_in[0].gl_Position;
        EmitVertex();
        gl_Position = gl_in[2].gl_Position;
        EmitVertex();
        gl_Position = gl_in[4].gl_Position;
        EmitVertex();
        EndPrimitive();
    }
}

GLSLShader ShaderPixel {
    void main() {
        colorOut = ps_in.gColor;
    }
}

technique Main
<
    string index_buffer_type = "GLSL_TRIADJ";
>
{
    pass P0
    <
        string drawContext = "colorPass";
    >
    {
        VertexShader (in VS_INPUT, out VS_TO_GEO geo_out) = ShaderVertex;
        GeometryShader (in VS_TO_GEO geo_in, out GEO_TO_PS geo_out) = ShaderGeometry;
        PixelShader (in GEO_TO_PS ps_in, out PS_OUT) = ShaderPixel;
    }
}
"""
        return shaderCode


class footPrintDrawOverride(omr.MPxDrawOverride):
    @classmethod
    def creator(cls, obj):
        return cls(obj)

    def __init__(self, obj):
        super(footPrintDrawOverride, self).__init__(obj, drawCallback)
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
        if not isinstance(data, footPrintData):
            data = footPrintData()

        data.fMultiplier = 1
        color = omr.MGeometryUtilities.wireframeColor(objPath)
        data.fColor = [color.r, color.g, color.b]
        data.fCustomBoxDraw = False

        data.fDrawOV = objPath.getDrawOverrideInfo()

        return data


def initializePlugin2(obj):
    plugin = om.MFnPlugin(obj, "Autodesk", "3.0", "Any")
    plugin.registerNode("footPrint",
                        footPrint.id,
                        footPrint.creator,
                        footPrint.initialize,
                        om.MPxNode.kLocatorNode,
                        footPrint.drawDbClassification)

    omr.MDrawRegistry.registerDrawOverrideCreator(
        footPrint.drawDbClassification,
        footPrint.drawRegistrantId,
        footPrintDrawOverride.creator
    )


def uninitializePlugin2(obj):
    plugin = om.MFnPlugin(obj)
    plugin.deregisterNode(footPrint.id)

    omr.MDrawRegistry.deregisterDrawOverrideCreator(
        footPrint.drawDbClassification,
        footPrint.drawRegistrantId
    )
