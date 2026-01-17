# io_scene_xrm
A Blender 3.X/4.X+ **work-in-progress** plugin to import and export models for Legacy of Kain: Soul Reaver I-II Remastered and Tomb Raider I-V Remastered models, Expect it to be updated in the near future.
***(THIS PLUGIN WAS TESTED WITH STEAM VERSIONS OF THE GAMES, OTHER VERSIONS ARE UNTESTED!)***

# Features
- **Global**: Functions and parsers are well-documented and print information in the System Console. *(In case you're curious or troubleshooting)*
- **Models**: An import option to import the game's original normals or to recalculate them. *(Looks smoother)*
- **Models**: An import option to import the model's textures which also sets up the shaders in each material node used by the model.
- **Models**: The ability to assign random colors to materials or not. *(To help with distinguishing submeshes)*
- **Models**: **VERY experimental custom model export support**

# Quick Model Export Instructions:
### You're limited to 65535 triangles in total and there's no limit to how many materials you can have
1. Normalize all of your model's weights and limit totals to 3
   - *(This is important because I haven't added an automated check for this yet)*
2. Only have what you want to export in the Blender scene, Anything you don't want make sure to remove it
3. **SOUL REAVER ONLY**: During export, Select the original model that you're planning on replacing then click the export button
   - *(This is important so it copies over some original data needed for it to finish exporting)*
4. Rename your custom model to the one you wanted to replace it then actually replace the file and test it in-game

# Credits
- Aspyr, Saber Interactive and the developers that worked on these awesome remasters
- MuruCoder for initial research of the TRM format