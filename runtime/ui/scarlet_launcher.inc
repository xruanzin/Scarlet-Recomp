// Scarlet-specific start screen, in the same SDL3/ImGui/Vulkan window as the game.
// Layout follows the compact dark, centered ImGui launcher of the old scarlet_pc.
// No graphics/upscaling controls here: keep that in the game's own settings.
// Included from launcher.mm only in SCARLET_AOT builds.
#include <fstream>
#include <sstream>
#include <thread>

namespace {
struct ScarletPick {
    std::string base, update, dlc1, dlc2, prod, title;
};
static pthread_mutex_t scarlet_pick_lock = PTHREAD_MUTEX_INITIALIZER;
static ScarletPick scarlet_pick;
static std::atomic<int> scarlet_install_state{0}; // 0 idle; 1 importing; 2 ok; 3 failed
static std::string scarlet_install_error;
static const char *const scarlet_root = "scarlet-games/active";
static const char *const scarlet_stage = "scarlet-games/.installing";
static const char *const scarlet_backup = "scarlet-games/previous";
static bool scarlet_ui_play;
static bool scarlet_60;
static void scarlet_load_fps_choice() {
    std::ifstream f("scarlet-games/native60.txt");
    char c = 0;
    if (f.get(c)) scarlet_60 = c == '1';
    else scarlet_60 = getenv("SCARLET_FPS60") && !strcmp(getenv("SCARLET_FPS60"), "1");
}
static void scarlet_save_fps_choice() {
    SDL_CreateDirectory("scarlet-games");
    std::ofstream f("scarlet-games/native60.txt",std::ios::trunc);
    if (f) f << (scarlet_60 ? "1\n" : "0\n");
#ifdef _WIN32
    _putenv_s("SCARLET_FPS60",scarlet_60 ? "1" : "0");
#else
    setenv("SCARLET_FPS60",scarlet_60 ? "1" : "0",1);
#endif
}

static bool scarlet_main_ok(const std::string &dir) {
    std::string path = dir + "/exefs/main";
    FILE *f = fopen(path.c_str(), "rb");
    if (!f) return false;
    unsigned char id[8] = {};
    bool ok = fseek(f, 0x40, SEEK_SET) == 0 && fread(id, 1, 8, f) == 8;
    fclose(f);
    static const unsigned char expected[8] = {0x42,0x1c,0x54,0x11,0xb4,0x87,0xeb,0x4d};
    return ok && !memcmp(id, expected, sizeof id);
}
static bool scarlet_imported(void) {
    return scarlet_main_ok(scarlet_root) &&
           (file_exists(std::string(scarlet_root)+"/romfs.bin") ||
            is_dir(std::string(scarlet_root)+"/romfs"));
}
static void scarlet_save_picks(const ScarletPick &p) {
    SDL_CreateDirectory("scarlet-games");
    std::ofstream f("scarlet-games/selection.txt", std::ios::trunc);
    if (!f) return;
    f << p.base << '\n' << p.update << '\n' << p.dlc1 << '\n'
      << p.dlc2 << '\n' << p.prod << '\n' << p.title << '\n';
}
static void scarlet_load_picks() {
    std::ifstream f("scarlet-games/selection.txt");
    if (!f) return;
    ScarletPick p;
    std::getline(f,p.base); std::getline(f,p.update);
    std::getline(f,p.dlc1); std::getline(f,p.dlc2);
    std::getline(f,p.prod); std::getline(f,p.title);
    pthread_mutex_lock(&scarlet_pick_lock);
    scarlet_pick = p;
    pthread_mutex_unlock(&scarlet_pick_lock);
}
static void SDLCALL scarlet_picked(void *ud, const char *const *files, int) {
    if (!files || !files[0]) return;
    int slot = (int)(intptr_t)ud;
    pthread_mutex_lock(&scarlet_pick_lock);
    std::string s = files[0];
    switch (slot) {
    case 0: scarlet_pick.base=s; break;
    case 1: scarlet_pick.update=s; break;
    case 2: scarlet_pick.dlc1=s; break;
    case 3: scarlet_pick.dlc2=s; break;
    case 4: scarlet_pick.prod=s; break;
    case 5: scarlet_pick.title=s; break;
    }
    pthread_mutex_unlock(&scarlet_pick_lock);
}
static void scarlet_choose(SDL_Window *win, int slot) {
    static const SDL_DialogFileFilter packages[]={{"Nintendo Switch dump", "nsp;xci"}};
    static const SDL_DialogFileFilter updates[]={{"Update or DLC", "nsp"}};
    static const SDL_DialogFileFilter keys[]={{"Nintendo Switch keys", "keys;txt"}};
    const SDL_DialogFileFilter *f = slot==4 || slot==5 ? keys : slot==0 ? packages : updates;
    SDL_ShowOpenFileDialog(scarlet_picked, (void *)(intptr_t)slot, win, f, 1, NULL, false);
}
static std::string scarlet_import_log_tail() {
    std::ifstream f("scarlet-games/import.log");
    if (!f) return "";
    std::string line, last;
    while (std::getline(f,line)) {
        if (line.rfind("progress ",0)!=0 && !line.empty()) last=line;
    }
    return last;
}
static void scarlet_import_worker(ScarletPick p) {
    std::string error;
    char tool[1100]={};
#ifdef _WIN32
    const char *exe = "scarletimport.exe";
#else
    const char *exe = "scarletimport";
#endif
    std::string in_app = std::string("scarletimport/")+exe;
    std::string in_build = std::string("build/scarletimport/")+exe;
    if (!rt_resource(in_app.c_str(),in_build.c_str(),tool,sizeof tool)) {
        error="scarletimport.exe ausente. Compile tools/scarletimport com dotnet publish.";
    } else {
        SDL_CreateDirectory("scarlet-games");
        // A failed/interrupted first use is never silently reused or deleted.
        // Move it aside for diagnostics, then start from a fresh staging dir.
        if (is_dir(scarlet_stage)) {
            if (is_dir("scarlet-games/failed") ||
                rename(scarlet_stage, "scarlet-games/failed") != 0)
                error="A importacao anterior permanece em .installing. Preserve/renomeie .installing e failed antes de tentar novamente.";
        }
        if (error.empty()) SDL_CreateDirectory(scarlet_stage);
        if (error.empty()) {
        std::vector<std::string> argv_store = {tool};
        if (!p.title.empty()) { argv_store.push_back("--title-keys"); argv_store.push_back(p.title); }
        argv_store.push_back(p.prod);
        argv_store.push_back(scarlet_stage);
        argv_store.push_back(p.base);
        if (!p.update.empty()) argv_store.push_back(p.update);
        if (!p.dlc1.empty()) argv_store.push_back(p.dlc1);
        if (!p.dlc2.empty()) argv_store.push_back(p.dlc2);
        std::vector<const char *> args;
        for (const auto &a:argv_store) args.push_back(a.c_str());
        args.push_back(NULL);
        PlatProc process=plat_spawn(args.data(),"scarlet-games/import.log",false);
        if (!process) error="Nao foi possivel executar scarletimport.exe.";
        else {
            int code=plat_proc_wait(process,true);
            if (code!=0) error="Falha de importacao: "+scarlet_import_log_tail();
            else if (!scarlet_main_ok(scarlet_stage)) error="Update 4.0.0 nao encontrado na extracao.";
            else {
                // Keep the prior installation on disk when reimporting;
                // never delete backups, saves, caches or the previous AOT.
                if (is_dir(scarlet_root)) {
                    if (is_dir(scarlet_backup))
                        error="Backup anterior em scarlet-games/previous: preserve ou renomeie antes de reimportar.";
                    else if (rename(scarlet_root,scarlet_backup)!=0)
                        error="Nao foi possivel preservar a instalacao anterior.";
                }
                if (error.empty() && rename(scarlet_stage,scarlet_root)!=0) {
                    error="Falha ao ativar novos arquivos; preservada pasta de staging.";
                    if (is_dir(scarlet_backup) && !is_dir(scarlet_root)) rename(scarlet_backup,scarlet_root);
                }
            }
        }
        } // staged importer
    }
    pthread_mutex_lock(&scarlet_pick_lock);
    scarlet_install_error=error;
    pthread_mutex_unlock(&scarlet_pick_lock);
    scarlet_install_state=error.empty()?2:3;
}
static void scarlet_line(SDL_Window *win,int slot,const char *name,const std::string &selected) {
    ImGui::TextUnformatted(name);
    ImGui::SameLine(175);
    ImGui::PushID(slot);
    if (ImGui::Button("Selecionar...",ImVec2(125,0))) scarlet_choose(win,slot);
    ImGui::PopID();
    if (!selected.empty()) {
        ImGui::SameLine();
        ImGui::TextDisabled("%s",selected.substr(selected.find_last_of("/\\")+1).c_str());
    }
}
} // namespace

extern "C" const char *scarlet_launcher_game_root(void) { return scarlet_root; }

static void scarlet_launch_run() {
    scarlet_load_picks();
    scarlet_load_fps_choice();
    scarlet_ui_play=false;
    ui_window_init();
    SDL_Window *win=ui_window();
    ImGuiContext *old=ImGui::GetCurrentContext();
    ImGuiContext *ctx=ImGui::CreateContext();
    ImGui::SetCurrentContext(ctx);
    ImGuiIO &io=ImGui::GetIO();
    io.IniFilename=NULL;
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    static const ImWchar latin[]={0x20,0xFF,0};
    if (!io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeui.ttf",21,NULL,latin))
        io.Fonts->AddFontDefault();
    ImGui::StyleColorsDark();
    ImGui::GetStyle().ScaleAllSizes(1.25f);
    ImGui_ImplSDL3_InitForVulkan(win);
    vk_imgui_backend_init();
    static const float bg[]={0.045f,0.055f,0.085f,1.0f};
    while (!scarlet_ui_play) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            ImGui_ImplSDL3_ProcessEvent(&e);
            if (e.type==SDL_EVENT_QUIT) exit(0);
        }
        if (!vk_frame_begin(bg)) {SDL_Delay(16);continue;}
        ImGui_ImplVulkan_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();
        ImGui::SetNextWindowPos(ImVec2(io.DisplaySize.x/2,io.DisplaySize.y/2),
                                ImGuiCond_Always,ImVec2(.5f,.5f));
        ImGui::SetNextWindowSize(ImVec2(820,0),ImGuiCond_Always);
        ImGui::Begin("SCARLET RECOMP",NULL,ImGuiWindowFlags_NoCollapse |
                     ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize |
                     ImGuiWindowFlags_AlwaysAutoResize);
        ImGui::TextColored(ImVec4(.96f,.38f,.34f,1),"POKEMON SCARLET  |  Windows / Vulkan");
        ImGui::SeparatorText("Arquivos do jogo - selecionar uma vez");
        ScarletPick p;
        pthread_mutex_lock(&scarlet_pick_lock);
        p=scarlet_pick;
        std::string error=scarlet_install_error;
        pthread_mutex_unlock(&scarlet_pick_lock);
        scarlet_line(win,0,"Jogo base NSP/XCI",p.base);
        scarlet_line(win,1,"Update 4.0.0 NSP",p.update);
        scarlet_line(win,2,"DLC NSP (Parte 1)",p.dlc1);
        scarlet_line(win,3,"DLC NSP (Parte 2)",p.dlc2);
        scarlet_line(win,4,"prod.keys",p.prod);
        scarlet_line(win,5,"title.keys (opcional)",p.title);
        ImGui::Spacing();
        const int state=scarlet_install_state.load();
        const bool installed=scarlet_imported();
        if (state==1) {
            ImGui::TextColored(ImVec4(.92f,.73f,.27f,1),"Importando / extraindo...");
            ImGui::TextWrapped("%s",scarlet_import_log_tail().c_str());
        } else if (state==3) {
            ImGui::TextColored(ImVec4(1,.45f,.45f,1),"%s",error.c_str());
        } else if (installed) {
            ImGui::TextColored(ImVec4(.35f,.86f,.54f,1),
                               "Pokémon Scarlet 4.0.0 extraido: pronto.");
        } else {
            ImGui::TextDisabled("Importe sua copia do jogo base, update 4.0.0 e DLC opcionais.");
        }
        ImGui::BeginDisabled(state==1 || p.base.empty() || p.update.empty() || p.prod.empty());
        if (ImGui::Button(installed?"Reimportar jogos/updates/DLC":"Extrair no primeiro uso",ImVec2(-FLT_MIN,42))) {
            scarlet_save_picks(p);
            scarlet_install_state=1;
            std::thread(scarlet_import_worker,p).detach();
        }
        ImGui::EndDisabled();
        ImGui::SeparatorText("Jogar");
        ImGui::Checkbox("60 FPS nativos (experimental)", &scarlet_60);
        if (ImGui::IsItemHovered())
            ImGui::SetTooltip("Clock Scarlet 4.0.0 + Vulkan 1 vsync. Valide velocidade da física, animações e batalhas.\n"
                              "Não garante 60 FPS quando CPU/GPU não sustentam 16,7 ms.");
        bool game_lib=installed && gamelib_present(scarlet_root);
        if (installed && !game_lib)
            ImGui::TextDisabled("AOT nao corresponde a este ExeFS: mantenha lasgame.dll e lasgame.dll.id da build Scarlet 4.0.0.");
        ImGui::BeginDisabled(state==1 || !game_lib);
        if (ImGui::Button("JOGAR",ImVec2(-FLT_MIN,48))) {
            scarlet_save_fps_choice();
            scarlet_ui_play=true;
        }
        ImGui::EndDisabled();
        ImGui::TextDisabled("Jogo e chaves nao incluidos. Os saves e cache ficam no diretorio de dados.");
        ImGui::End();
        ImGui::Render();
        ImGui_ImplVulkan_RenderDrawData(ImGui::GetDrawData(),(VkCommandBuffer)vk_frame_cmd());
        vk_frame_end(NULL);
    }
    vk_imgui_backend_shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext(ctx);
    ImGui::SetCurrentContext(old);
}
