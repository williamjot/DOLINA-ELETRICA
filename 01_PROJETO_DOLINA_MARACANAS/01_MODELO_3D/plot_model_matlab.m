% Plot the parametric cavity model and the two ERT lines.
root = fileparts(mfilename('fullpath'));
S = load(fullfile(root, 'dolina_model.mat'));

figure('Color','w');
trisurf(S.faces_open, S.vertices_open_local(:,1), S.vertices_open_local(:,2), ...
    S.vertices_open_local(:,3), -S.vertices_open_local(:,3), ...
    'EdgeColor','none','FaceAlpha',0.82);
hold on;
plot3(S.L1_xyz_local(:,1),S.L1_xyz_local(:,2),S.L1_xyz_local(:,3), ...
    'LineWidth',2.2,'Color',[0.09 0.29 0.49]);
plot3(S.L2_xyz_local(:,1),S.L2_xyz_local(:,2),S.L2_xyz_local(:,3), ...
    'LineWidth',2.2,'Color',[0.70 0.27 0.22]);
axis equal; grid on; view(45,25); colormap(flipud(parula));
xlabel('Leste local (m)'); ylabel('Norte local (m)'); zlabel('Cota relativa (m)');
title('Dolina dos Maracanas - modelo 3D interpretativo');
legend('Superficie da cavidade','L1','L2','Location','best');
camlight headlight; lighting gouraud;
