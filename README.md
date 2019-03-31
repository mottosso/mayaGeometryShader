### Maya Geometry Shader Example

..That doesn't work. Why?

<br>

### Usage

This example requires Viewport 2.0, to load it here's what you do and what you can expect to see.

```python
import pyDrawOverride
pyDrawOverride.install()

# Install a shader
dirname = os.path.dirname(pyDrawOverride.__file__)
fname = os.path.join(dirname, "noGeometryShader.ogsfx")
pyDrawOverride.effect = fname

# Draw the effect
node = cmds.createNode("DrawOverrideNode")
```

![glsl](https://user-images.githubusercontent.com/2152766/55281405-f6c02f00-532b-11e9-88fc-683a11b03e31.gif)

Now install the Geometry Shader instead.

```python
fname = os.path.join(dirname, "withGeometryShader.ogsfx")
pyDrawOverride.effect = fname
```

And presto! What was once drawn is drawn no more. It's gone, vanished. As though vertices are passed into the geometry shader and stays there. The pixel shader is left wondering about life.

<br>

### Why?

I would very much like for the geometry shader to output *something*, but I cannot. Any ideas?

Here's the geometry shader at work in the `glslShader` plug-in and `TesselationExample.ogsfx` example. So clearly, it does work. The only question is, how?

![glslGeo2](https://user-images.githubusercontent.com/2152766/55281512-82868b00-532d-11e9-924f-86411addade7.gif)
