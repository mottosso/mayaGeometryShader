### Maya Geometry Shader Example

..That doesn't work. Why?

<br>

### Usage

This example requires Viewport 2.0, to load it here's what you do and what you can expect to see.

```python
from maya import cmds

cmds.loadPlugin("path/to/pyDrawOverride.py")
cmds.createNode("DrawOverrideNode")
```

![glsl](https://user-images.githubusercontent.com/2152766/55281405-f6c02f00-532b-11e9-88fc-683a11b03e31.gif)

Now either copy/paste the contents of `withGeometryShader.ogsfx` into `noGeometryShader.ogsfx`, or edit the line containing `os.path.join(dirname, "noGeometryShader.ogsfx")` and reload.

```python
cmds.file(new=True, force=True)
cmds.unloadPlugin("pyDrawOverride")
cmds.unloadPlugin("path/to/pyDrawOverride.py")
cmds.createNode("DrawOverrideNode")
```

And presto! What was once drawn is drawn no more. It's gone, vanished. As though vertices are passed into the geometry shader and stays there. The pixel shader is left wondering about life.

<br>

### Why?

I would very much like for the geometry shader to output *something*, but I cannot. Any ideas?