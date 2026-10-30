function plot_resistivity_sections_matlab(l1file,l2file)
% Plot one or two numerical ERT sections in the cavity model.
% CSV fields: distance_m, elevation_m (or depth_m), resistivity_ohm_m.

root = fileparts(mfilename('fullpath'));
S = load(fullfile(root,'dolina_model.mat'));
figure('Color','w');
trisurf(S.faces_open,S.vertices_open_local(:,1),S.vertices_open_local(:,2), ...
    S.vertices_open_local(:,3),'FaceColor',[0.65 0.58 0.45], ...
    'FaceAlpha',0.12,'EdgeColor','none'); hold on;

rhoAll = [];
if nargin >= 1 && ~isempty(l1file)
    rhoAll = [rhoAll; addSection(S,'L1',l1file)]; %#ok<AGROW>
end
if nargin >= 2 && ~isempty(l2file)
    rhoAll = [rhoAll; addSection(S,'L2',l2file)]; %#ok<AGROW>
end
if isempty(rhoAll), error('Provide at least one numerical section CSV.'); end

set(gca,'ColorScale','log'); colormap(turbo); colorbar;
axis equal; grid on; view(45,25);
xlabel('Leste local (m)'); ylabel('Norte local (m)'); zlabel('Cota relativa (m)');
title('Secoes de eletrorresistividade na Dolina dos Maracanas');
end

function rho = addSection(S,key,file)
T = readtable(file);
station = S.([key '_station_m']);
line = S.([key '_xyz_local']);
x = interp1(station,line(:,1),T.distance_m,'linear');
y = interp1(station,line(:,2),T.distance_m,'linear');
if ismember('elevation_m',T.Properties.VariableNames)
    z = T.elevation_m - S.center_utm(3);
    vertical = T.elevation_m;
else
    top = interp1(station,line(:,3),T.distance_m,'linear');
    z = top - T.depth_m;
    vertical = T.depth_m;
end
tri = delaunay(T.distance_m,vertical);
trisurf(tri,x,y,z,T.resistivity_ohm_m,'EdgeColor','none','FaceAlpha',0.94);
rho = T.resistivity_ohm_m;
end
