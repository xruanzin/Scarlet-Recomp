#define UNICODE
#define _UNICODE
#define NOMINMAX
#include <windows.h>
#include <commctrl.h>
#include <commdlg.h>
#include <dwmapi.h>
#include <gdiplus.h>
#include <shellapi.h>
#include <shlwapi.h>
#include <uxtheme.h>

#include <algorithm>
#include <array>
#include <cwctype>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>
#include <atomic>
#include <fstream>
#include <shlobj.h>
#include <chrono>
#include <set>
#include <iterator>

#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "uxtheme.lib")

using namespace Gdiplus;
namespace fs = std::filesystem;

namespace {

constexpr wchar_t kWindowClass[] = L"ScarletPCLauncherWindow";
constexpr wchar_t kTitle[] = L"Scarlet";
constexpr int kWindowWidth = 1280;
constexpr int kWindowHeight = 760;
constexpr UINT kGameExitedMessage = WM_APP + 1;
constexpr UINT kImportFinishedMessage = WM_APP + 2;

enum ControlId : int {
    ID_TAB_GAME = 100,
    ID_TAB_GRAPHICS,
    ID_TAB_CONTROLS,
    ID_TAB_GENERAL,

    ID_GAME_EDIT = 200,
    ID_GAME_BROWSE,
    ID_UPDATE_EDIT,
    ID_UPDATE_BROWSE,
    ID_KEYS_EDIT,
    ID_KEYS_BROWSE,
    ID_DLC_LIST,
    ID_DLC_ADD,
    ID_DLC_REMOVE,
    ID_GAME_STATUS,

    ID_RESOLUTION = 300,
    ID_DISPLAY_MODE,
    ID_FPS,
    ID_UPSCALER,
    ID_UPSCALER_QUALITY,
    ID_FRAME_GENERATION,
    ID_ASYNC_SHADERS,

    ID_CONTROLLER_STYLE = 400,
    ID_AUTO_CONTROLLER,
    ID_CONTROLLER_HINT,

    ID_LANGUAGE = 500,
    ID_OPEN_USER,
    ID_OPEN_LOGS,
    ID_CLOSE_ON_LAUNCH,

    ID_PLAY = 900,
};

enum Page : int { Game = 0, Graphics = 1, Controls = 2, General = 3 };

struct ResolutionEntry {
    const wchar_t* label;
    int width;
    int height;
};

constexpr std::array<ResolutionEntry, 7> kResolutions{{
    {L"1366 x 768", 1366, 768},
    {L"1600 x 900", 1600, 900},
    {L"1920 x 1080", 1920, 1080},
    {L"1920 x 1200", 1920, 1200},
    {L"2560 x 1440", 2560, 1440},
    {L"2560 x 1600", 2560, 1600},
    {L"3840 x 2160", 3840, 2160},
}};

constexpr std::array<const wchar_t*, 3> kDisplayModes{{
    L"Janela", L"Borderless", L"Tela cheia"
}};

constexpr std::array<const wchar_t*, 5> kFpsModes{{
    L"30 FPS", L"60 FPS", L"120 FPS", L"144 FPS", L"Ilimitado"
}};

constexpr std::array<const wchar_t*, 6> kUpscalers{{
    L"Nativo", L"DLSS", L"FSR 1", L"FSR 3", L"FSR 3.1", L"FSR 4"
}};

constexpr std::array<const wchar_t*, 4> kUpscalerQualities{{
    L"Qualidade", L"Balanceado", L"Performance", L"Ultra Performance"
}};

constexpr std::array<const wchar_t*, 4> kControllerStyles{{
    L"Automático", L"Xbox", L"PlayStation", L"Nintendo"
}};

constexpr std::array<const wchar_t*, 2> kLanguages{{
    L"Português (Brasil)", L"English"
}};

HINSTANCE g_instance{};
ULONG_PTR g_gdiplus_token{};
std::unique_ptr<Image> g_background;
HBRUSH g_edit_brush{};
HBRUSH g_panel_brush{};
HFONT g_font{};
HFONT g_font_bold{};
HFONT g_font_large{};

HWND g_main{};
Page g_page = Game;
std::array<std::vector<HWND>, 4> g_page_controls;

HWND g_game_edit{};
HWND g_update_edit{};
HWND g_keys_edit{};
HWND g_dlc_list{};
HWND g_status{};

HWND g_resolution{};
HWND g_display_mode{};
HWND g_fps{};
HWND g_upscaler{};
HWND g_quality{};
HWND g_frame_generation{};
HWND g_async_shaders{};

HWND g_controller_style{};
HWND g_auto_controller{};

HWND g_language{};
HWND g_close_on_launch{};

// Additional user-picked NSP/XCI and folders: no slot or count limit.
std::vector<std::wstring> g_dlcs;
std::vector<std::wstring> g_extra_folders;
struct PackageItem { std::wstring label; int kind; size_t index; };
std::vector<PackageItem> g_visible_packages;
std::wstring g_status_text;
std::atomic<bool> g_importing{false};
std::wstring g_import_error;
fs::path g_exe_dir;
fs::path g_ini_path;

struct GameWaitContext {
    HANDLE process{};
    HWND launcher{};
};

DWORD WINAPI WaitForGameProcess(LPVOID opaque) {
    std::unique_ptr<GameWaitContext> context(static_cast<GameWaitContext*>(opaque));
    WaitForSingleObject(context->process, INFINITE);
    DWORD exit_code = 0;
    GetExitCodeProcess(context->process, &exit_code);
    CloseHandle(context->process);
    PostMessageW(context->launcher, kGameExitedMessage, static_cast<WPARAM>(exit_code), 0);
    return 0;
}

std::wstring GetText(HWND hwnd) {
    const int len = GetWindowTextLengthW(hwnd);
    if (len <= 0) return {};
    std::wstring text(static_cast<size_t>(len) + 1, L'\0');
    GetWindowTextW(hwnd, text.data(), len + 1);
    text.resize(static_cast<size_t>(len));
    return text;
}

void SetText(HWND hwnd, const std::wstring& text) {
    SetWindowTextW(hwnd, text.c_str());
}

std::wstring IniRead(const wchar_t* section, const wchar_t* key, const wchar_t* fallback = L"") {
    std::array<wchar_t, 32768> buffer{};
    GetPrivateProfileStringW(section, key, fallback, buffer.data(),
                             static_cast<DWORD>(buffer.size()), g_ini_path.c_str());
    return buffer.data();
}

int IniReadInt(const wchar_t* section, const wchar_t* key, int fallback) {
    return static_cast<int>(GetPrivateProfileIntW(section, key, fallback, g_ini_path.c_str()));
}

void IniWrite(const wchar_t* section, const wchar_t* key, const std::wstring& value) {
    WritePrivateProfileStringW(section, key, value.c_str(), g_ini_path.c_str());
}

void IniWriteInt(const wchar_t* section, const wchar_t* key, int value) {
    IniWrite(section, key, std::to_wstring(value));
}

fs::path ExeDir() {
    std::array<wchar_t, 32768> path{};
    GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    return fs::path(path.data()).parent_path();
}

std::wstring QuoteArg(const std::wstring& arg) {
    if (arg.empty()) return L"\"\"";
    if (arg.find_first_of(L" \t\n\v\"") == std::wstring::npos) return arg;
    std::wstring out = L"\"";
    unsigned slashes = 0;
    for (wchar_t ch : arg) {
        if (ch == L'\\') {
            ++slashes;
            continue;
        }
        if (ch == L'"') {
            out.append(slashes * 2 + 1, L'\\');
            out.push_back(L'"');
            slashes = 0;
            continue;
        }
        out.append(slashes, L'\\');
        slashes = 0;
        out.push_back(ch);
    }
    out.append(slashes * 2, L'\\');
    out.push_back(L'"');
    return out;
}

bool FileExists(const std::wstring& path) {
    std::error_code ec;
    return !path.empty() && fs::is_regular_file(fs::path(path), ec);
}

bool HasExtension(const std::wstring& path, std::initializer_list<const wchar_t*> exts) {
    std::wstring ext = fs::path(path).extension().wstring();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::towlower);
    for (const auto* allowed : exts) {
        if (ext == allowed) return true;
    }
    return false;
}

std::wstring OpenFile(HWND owner, const wchar_t* filter, const std::wstring& initial = {}) {
    std::array<wchar_t, 32768> file{};
    if (!initial.empty() && initial.size() < file.size()) {
        wcscpy_s(file.data(), file.size(), initial.c_str());
    }

    OPENFILENAMEW ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = owner;
    ofn.lpstrFilter = filter;
    ofn.lpstrFile = file.data();
    ofn.nMaxFile = static_cast<DWORD>(file.size());
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_EXPLORER;
    if (!GetOpenFileNameW(&ofn)) return {};
    return file.data();
}

std::wstring OpenPackageFolder(HWND owner) {
    BROWSEINFOW bi{};
    bi.hwndOwner = owner;
    bi.lpszTitle = L"Selecionar pasta do jogo";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE pid = SHBrowseForFolderW(&bi);
    if (!pid) return {};
    std::array<wchar_t, 32768> folder{};
    bool ok = SHGetPathFromIDListW(pid, folder.data()) != FALSE;
    CoTaskMemFree(pid);
    return ok ? std::wstring(folder.data()) : std::wstring();
}
static std::string Utf8(const std::wstring& s) {
    int n = WideCharToMultiByte(CP_UTF8, 0, s.c_str(), (int)s.size(),
                               nullptr, 0, nullptr, nullptr);
    if (n <= 0) return {};
    std::string result((size_t)n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, s.c_str(), (int)s.size(),
                        result.data(), n, nullptr, nullptr);
    return result;
}
static bool IsPackage(const fs::path& p) {
    std::wstring ext=p.extension().wstring();
    std::transform(ext.begin(),ext.end(),ext.begin(),::towlower);
    return ext == L".nsp" || ext == L".xci";
}
static std::wstring Fold(const fs::path& path) {
    std::error_code ec;
    fs::path p = fs::absolute(path,ec);
    if (ec) p=path;
    auto value=p.lexically_normal().wstring();
    std::transform(value.begin(),value.end(),value.begin(),::towlower);
    return value;
}
static void ScanFolder(const fs::path& dir,
                       std::vector<fs::path>& all,
                       std::set<std::wstring>& visited) {
    std::error_code ec;
    if (!fs::is_directory(dir,ec)) return;
    for (fs::recursive_directory_iterator it(dir,
              fs::directory_options::skip_permission_denied,ec), end;
         it != end && !ec; it.increment(ec)) {
        if (it->is_regular_file(ec) && IsPackage(it->path())) {
            const auto key=Fold(it->path());
            if (visited.insert(key).second) all.push_back(it->path());
        }
        if (ec) ec.clear();
    }
}
static std::vector<fs::path> PackageFiles(const fs::path& dir) {
    std::vector<fs::path> all;
    std::set<std::wstring> visited;
    ScanFolder(dir,all,visited);
    for (const auto& p:g_extra_folders) ScanFolder(p,all,visited);
    for (const auto& p:g_dlcs) {
        std::error_code ec;
        if (fs::is_regular_file(p,ec) && IsPackage(p) &&
            visited.insert(Fold(p)).second) all.emplace_back(p);
    }
    std::sort(all.begin(),all.end(),[](const fs::path& a,const fs::path& b){
        return Fold(a)<Fold(b);
    });
    return all;
}
static fs::path FindKeys(const fs::path& dir, const wchar_t *name) {
    for (const auto& base : {dir, dir / L"keys", g_exe_dir / L"keys",
                             g_exe_dir / L"user" / L"keys", g_exe_dir}) {
        fs::path file = base / name;
        std::error_code ec;
        if (fs::is_regular_file(file, ec)) return file;
    }
    return {};
}
static fs::path InstalledRoot() { return g_exe_dir / L"scarlet-games" / L"active"; }
static bool Installed() {
    std::error_code ec;
    auto root = InstalledRoot();
    if (!fs::is_regular_file(root / L"romfs.bin", ec) ||
        !fs::is_regular_file(root / L"exefs" / L"main", ec)) return false;
    std::ifstream f(root / L"exefs" / L"main", std::ios::binary);
    if (!f.seekg(0x40)) return false;
    std::array<unsigned char, 8> bid{};
    f.read((char*)bid.data(), (std::streamsize)bid.size());
    constexpr std::array<unsigned char, 8> expected = {0x42,0x1c,0x54,0x11,0xb4,0x87,0xeb,0x4d};
    return f.gcount() == (std::streamsize)bid.size() && bid == expected;
}
static std::string PackageStamp(const std::vector<fs::path>& packages) {
    std::string stamp;
    for (const auto& p: packages) {
        std::error_code ec;
        auto bytes = fs::file_size(p, ec);
        auto stampTime = fs::last_write_time(p, ec).time_since_epoch().count();
        stamp += Utf8(p.wstring()) + "|" + std::to_string(bytes) + "|" +
                 std::to_string(stampTime) + "\n";
    }
    return stamp;
}
static bool InstallMatches(const std::vector<fs::path>& packages) {
    if (!Installed()) return false;
    std::ifstream f(InstalledRoot() / L"source.fingerprint.txt", std::ios::binary);
    std::string actual((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    return !actual.empty() && actual == PackageStamp(packages);
}
static std::wstring LastImportLine() {
    std::ifstream f(g_exe_dir / L"scarlet-games" / L"import.log");
    std::string s,line;
    while (std::getline(f,line)) if (!line.empty() && line.rfind("progress ",0) != 0) s=line;
    if (s.empty()) return L"Importação em andamento...";
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), NULL, 0);
    if (n<=0) return L"Importação em andamento...";
    std::wstring out((size_t)n,L'\0');
    MultiByteToWideChar(CP_UTF8,0,s.c_str(),(int)s.size(),out.data(),n);
    return out;
}

void AddToPage(Page page, HWND hwnd) {
    g_page_controls[static_cast<size_t>(page)].push_back(hwnd);
}

HWND MakeStatic(Page page, int x, int y, int w, int h, const wchar_t* text, bool bold = false) {
    HWND hnd = CreateWindowExW(0, L"STATIC", text, WS_CHILD | WS_VISIBLE | SS_LEFT,
                               x, y, w, h, g_main, nullptr, g_instance, nullptr);
    SendMessageW(hnd, WM_SETFONT, reinterpret_cast<WPARAM>(bold ? g_font_bold : g_font), TRUE);
    AddToPage(page, hnd);
    return hnd;
}

HWND MakeEdit(Page page, int id, int x, int y, int w, int h) {
    HWND hnd = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
                               WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL | WS_TABSTOP,
                               x, y, w, h, g_main, reinterpret_cast<HMENU>(id), g_instance, nullptr);
    SendMessageW(hnd, WM_SETFONT, reinterpret_cast<WPARAM>(g_font), TRUE);
    SetWindowTheme(hnd, L"DarkMode_Explorer", nullptr);
    AddToPage(page, hnd);
    return hnd;
}

HWND MakeButton(Page page, int id, int x, int y, int w, int h, const wchar_t* text) {
    HWND hnd = CreateWindowExW(0, L"BUTTON", text,
                               WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_OWNERDRAW,
                               x, y, w, h, g_main, reinterpret_cast<HMENU>(id), g_instance, nullptr);
    SendMessageW(hnd, WM_SETFONT, reinterpret_cast<WPARAM>(g_font_bold), TRUE);
    AddToPage(page, hnd);
    return hnd;
}

HWND MakeCombo(Page page, int id, int x, int y, int w, int h,
               const wchar_t* const* items, size_t count, int selection) {
    HWND hnd = CreateWindowExW(0, WC_COMBOBOXW, L"",
                               WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST | WS_VSCROLL,
                               x, y, w, h, g_main, reinterpret_cast<HMENU>(id), g_instance, nullptr);
    SendMessageW(hnd, WM_SETFONT, reinterpret_cast<WPARAM>(g_font), TRUE);
    SetWindowTheme(hnd, L"DarkMode_Explorer", nullptr);
    for (size_t i = 0; i < count; ++i) {
        SendMessageW(hnd, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(items[i]));
    }
    SendMessageW(hnd, CB_SETCURSEL, std::clamp(selection, 0, static_cast<int>(count) - 1), 0);
    AddToPage(page, hnd);
    return hnd;
}

template <size_t N>
HWND MakeCombo(Page page, int id, int x, int y, int w, int h,
               const std::array<const wchar_t*, N>& items, int selection) {
    return MakeCombo(page, id, x, y, w, h, items.data(), items.size(), selection);
}

HWND MakeCheckbox(Page page, int id, int x, int y, int w, int h,
                  const wchar_t* text, bool checked) {
    HWND hnd = CreateWindowExW(0, L"BUTTON", text,
                               WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
                               x, y, w, h, g_main, reinterpret_cast<HMENU>(id), g_instance, nullptr);
    SendMessageW(hnd, WM_SETFONT, reinterpret_cast<WPARAM>(g_font), TRUE);
    SendMessageW(hnd, BM_SETCHECK, checked ? BST_CHECKED : BST_UNCHECKED, 0);
    SetWindowTheme(hnd, L"DarkMode_Explorer", nullptr);
    AddToPage(page, hnd);
    return hnd;
}

void RefreshDlcList() {
    if (!g_dlc_list) return;
    SendMessageW(g_dlc_list,WM_SETREDRAW,FALSE,0);
    SendMessageW(g_dlc_list,LB_RESETCONTENT,0,0);
    g_visible_packages.clear();
    const auto found=PackageFiles(GetText(g_game_edit));
    for (const auto& p: found) {
        auto item=L"  "+p.filename().wstring();
        LRESULT i=SendMessageW(g_dlc_list,LB_ADDSTRING,0,(LPARAM)item.c_str());
        if (i>=0) g_visible_packages.push_back({item,0,0});
    }
    for (size_t i=0;i<g_dlcs.size();++i) {
        auto label=L"  + NSP: "+fs::path(g_dlcs[i]).filename().wstring();
        LRESULT pos=SendMessageW(g_dlc_list,LB_ADDSTRING,0,(LPARAM)label.c_str());
        if (pos>=0) g_visible_packages.push_back({label,1,i});
    }
    for (size_t i=0;i<g_extra_folders.size();++i) {
        auto label=L"  + Pasta: "+fs::path(g_extra_folders[i]).filename().wstring();
        LRESULT pos=SendMessageW(g_dlc_list,LB_ADDSTRING,0,(LPARAM)label.c_str());
        if (pos>=0) g_visible_packages.push_back({label,2,i});
    }
    SendMessageW(g_dlc_list,WM_SETREDRAW,TRUE,0);
    InvalidateRect(g_dlc_list,nullptr,TRUE);
}

void RefreshStatus() {
    const auto packages=PackageFiles(GetText(g_game_edit));
    if (g_importing.load()) g_status_text=L"Preparando arquivos...";
    else if (packages.empty()) g_status_text=L"Nenhum NSP/XCI selecionado";
    else {
        g_status_text=std::to_wstring(packages.size())+L" pacote(s) selecionado(s)";
        if (InstallMatches(packages)) g_status_text+=L"     Pronto";
    }
    RefreshDlcList();
    RECT r{290,516,1140,610};
    InvalidateRect(g_main,&r,FALSE);
}

void ShowPage(Page page) {
    g_page = page;
    for (size_t i = 0; i < g_page_controls.size(); ++i) {
        for (HWND control : g_page_controls[i]) {
            ShowWindow(control, i == static_cast<size_t>(page) ? SW_SHOW : SW_HIDE);
        }
    }
    InvalidateRect(g_main, nullptr, TRUE);
}

void SetComboSelection(HWND combo, int index) {
    const int count = static_cast<int>(SendMessageW(combo, CB_GETCOUNT, 0, 0));
    if (count > 0) SendMessageW(combo, CB_SETCURSEL, std::clamp(index, 0, count - 1), 0);
}

int ComboSelection(HWND combo) {
    const LRESULT value = SendMessageW(combo, CB_GETCURSEL, 0, 0);
    return value == CB_ERR ? 0 : static_cast<int>(value);
}

bool Checked(HWND checkbox) {
    return SendMessageW(checkbox, BM_GETCHECK, 0, 0) == BST_CHECKED;
}

void SaveSettings() {
    std::error_code ec;
    fs::create_directories(g_ini_path.parent_path(),ec);
    IniWrite(L"Game",L"directory",GetText(g_game_edit));
    std::ofstream f(g_ini_path.parent_path()/L"scarlet_extra_packages.txt",
                    std::ios::binary|std::ios::trunc);
    for (const auto& p:g_dlcs) f << "F" << Utf8(p) << "\n";
    for (const auto& p:g_extra_folders) f << "D" << Utf8(p) << "\n";
}
static std::wstring Utf8ToWide(const std::string& s) {
    int n=MultiByteToWideChar(CP_UTF8,0,s.data(),(int)s.size(),nullptr,0);
    if (n<=0) return {};
    std::wstring out((size_t)n,L'\0');
    MultiByteToWideChar(CP_UTF8,0,s.data(),(int)s.size(),out.data(),n);
    return out;
}

void LoadSettings() {
    auto folder=IniRead(L"Game",L"directory");
    if (folder.empty()) {
        auto oldGame=IniRead(L"Game",L"game");
        if (FileExists(oldGame)) folder=fs::path(oldGame).parent_path().wstring();
    }
    g_dlcs.clear();
    g_extra_folders.clear();
    std::ifstream f(g_ini_path.parent_path()/L"scarlet_extra_packages.txt",std::ios::binary);
    std::string item;
    while (std::getline(f,item)) {
        if (item.size()<2) continue;
        if (item[0]=='F') g_dlcs.push_back(Utf8ToWide(item.substr(1)));
        if (item[0]=='D') g_extra_folders.push_back(Utf8ToWide(item.substr(1)));
    }
    SetText(g_game_edit,folder);
    RefreshStatus();
}

void OpenFolder(const fs::path& path) {
    std::error_code ec;
    fs::create_directories(path, ec);
    ShellExecuteW(g_main, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

std::wstring UpscalerEnv(int index) {
    switch (index) {
    case 1: return L"dlss";
    case 2: return L"fsr1";
    case 3: return L"fsr3";
    case 4: return L"fsr31";
    case 5: return L"fsr4";
    default: return L"native";
    }
}

std::wstring QualityEnv(int index) {
    switch (index) {
    case 1: return L"balanced";
    case 2: return L"performance";
    case 3: return L"ultra_performance";
    default: return L"quality";
    }
}

std::wstring DisplayModeEnv(int index) {
    switch (index) {
    case 1: return L"borderless";
    case 2: return L"fullscreen";
    default: return L"windowed";
    }
}

int TargetFpsValue(int index) {
    switch (index) {
    case 0: return 30;
    case 2: return 120;
    case 3: return 144;
    case 4: return 240; // practical "unlimited" ceiling used by the runtime
    default: return 60;
    }
}

void SetChildEnvironment(int width, int height) {
    SetEnvironmentVariableW(L"NSWITCH_AOT_FALLBACK", L"1");
    SetEnvironmentVariableW(L"SCARLET_TARGET_FPS",
                            std::to_wstring(TargetFpsValue(ComboSelection(g_fps))).c_str());
    SetEnvironmentVariableW(L"SCARLET_ASYNC_SHADERS",
                            Checked(g_async_shaders) ? L"1" : L"0");
    SetEnvironmentVariableW(L"SCARLET_WINDOW_MODE",
                            DisplayModeEnv(ComboSelection(g_display_mode)).c_str());
    SetEnvironmentVariableW(L"SCARLET_WINDOW_WIDTH", std::to_wstring(width).c_str());
    SetEnvironmentVariableW(L"SCARLET_WINDOW_HEIGHT", std::to_wstring(height).c_str());
    SetEnvironmentVariableW(L"SCARLET_UPSCALER",
                            UpscalerEnv(ComboSelection(g_upscaler)).c_str());
    SetEnvironmentVariableW(L"SCARLET_UPSCALER_QUALITY",
                            QualityEnv(ComboSelection(g_quality)).c_str());
    SetEnvironmentVariableW(L"SCARLET_FRAME_GENERATION",
                            Checked(g_frame_generation) ? L"1" : L"0");
    SetEnvironmentVariableW(L"SCARLET_CONTROLLER_STYLE",
                            std::to_wstring(ComboSelection(g_controller_style)).c_str());
    SetEnvironmentVariableW(L"SCARLET_AUTO_CONTROLLER",
                            Checked(g_auto_controller) ? L"1" : L"0");
}

bool PrepareKeys(const std::wstring& selected) {
    if (!FileExists(selected)) return false;
    const fs::path keys_dir = g_exe_dir / L"user" / L"keys";
    std::error_code ec;
    fs::create_directories(keys_dir, ec);
    const fs::path target = keys_dir / L"prod.keys";
    if (!CopyFileW(selected.c_str(), target.c_str(), FALSE)) {
        if (GetLastError() != ERROR_SHARING_VIOLATION && GetLastError() != ERROR_ACCESS_DENIED) {
            return false;
        }
        // If it is the same file already in use, it is still valid for launching.
        if (!fs::equivalent(fs::path(selected), target, ec)) return false;
    }
    return true;
}

static bool RunProcess(const fs::path& exe, const std::wstring& args,
                       const fs::path& log, DWORD* exitCode) {
    std::wstring command = QuoteArg(exe.wstring()) + L" " + args;
    std::vector<wchar_t> mutableCmd(command.begin(),command.end());
    mutableCmd.push_back(L'\0');
    STARTUPINFOW si{}; si.cb=sizeof si;
    PROCESS_INFORMATION pi{};
    HANDLE logfile = CreateFileW(log.c_str(), GENERIC_WRITE, FILE_SHARE_READ,
                                 nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    HANDLE input = CreateFileW(L"NUL", GENERIC_READ,
                              FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    const bool redirect = logfile != INVALID_HANDLE_VALUE && input != INVALID_HANDLE_VALUE;
    if (redirect) {
        SetHandleInformation(logfile,HANDLE_FLAG_INHERIT,HANDLE_FLAG_INHERIT);
        SetHandleInformation(input,HANDLE_FLAG_INHERIT,HANDLE_FLAG_INHERIT);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = logfile; si.hStdError=logfile; si.hStdInput=input;
    }
    BOOL ok = CreateProcessW(exe.c_str(), mutableCmd.data(),nullptr,nullptr,
                             redirect, CREATE_NO_WINDOW,
                             nullptr,g_exe_dir.c_str(),&si,&pi);
    if (logfile != INVALID_HANDLE_VALUE) CloseHandle(logfile);
    if (input != INVALID_HANDLE_VALUE) CloseHandle(input);
    if (!ok) return false;
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code=1;
    GetExitCodeProcess(pi.hProcess,&code);
    CloseHandle(pi.hProcess);
    if (exitCode) *exitCode=code;
    return true;
}
static bool ImportPackages(const fs::path& folder, std::wstring* error) {
    auto packages = PackageFiles(folder);
    if (packages.empty()) { *error=L"Nenhum NSP ou XCI encontrado."; return false; }
    fs::path keys=FindKeys(folder,L"prod.keys");
    if (keys.empty()) { *error=L"prod.keys não encontrado."; return false; }
    fs::path importer=g_exe_dir / L"scarletimport" / L"scarletimport.exe";
    if (!FileExists(importer.wstring())) { *error=L"scarletimport.exe não encontrado."; return false; }
    if (InstallMatches(packages)) return true;
    fs::path games=g_exe_dir / L"scarlet-games";
    fs::path stage=games / L".installing";
    fs::path active=games / L"active";
    std::error_code ec;
    fs::create_directories(games,ec);
    if (fs::exists(stage,ec)) {
        // Keep all interrupted imports; do not overwrite or delete user data.
        fs::path failed=games / (L"failed-" + std::to_wstring(GetTickCount64()));
        fs::rename(stage,failed,ec);
        if (ec) {
            *error=L"Não foi possível preservar a importação anterior.";
            return false;
        }
    }
    fs::create_directories(stage,ec);
    if (ec) { *error=L"Falha ao criar pasta de importação."; return false; }
    // Package-list file avoids the Windows ~32k command-line limit. No hard
    // cap on DLC count: the importer reads every .nsp/.xci listed here.
    fs::path manifest=stage / L"packages.txt";
    {
        std::ofstream out(manifest,std::ios::binary);
        for (const auto& path:packages) out << Utf8(path.wstring()) << "\n";
        if (!out) { *error=L"Falha ao salvar lista de pacotes."; return false; }
    }
    fs::path title=FindKeys(folder,L"title.keys");
    std::wstring args;
    if (!title.empty()) args=L"--title-keys " + QuoteArg(title.wstring()) + L" ";
    args+=QuoteArg(keys.wstring()) + L" " + QuoteArg(stage.wstring()) +
          L" --packages-file " + QuoteArg(manifest.wstring());
    DWORD code=1;
    if (!RunProcess(importer,args,games / L"import.log",&code) || code!=0 ||
        !fs::exists(stage / L"romfs.bin") ||
        !fs::exists(stage / L"exefs" / L"main")) {
        *error=L"Falha ao importar. Consulte scarlet-games\\import.log.";
        return false;
    }
    {
        std::ofstream out(stage / L"source.fingerprint.txt",std::ios::binary);
        out << PackageStamp(packages);
        if (!out) { *error=L"Falha ao salvar estado do jogo."; return false; }
    }
    if (fs::exists(active,ec)) {
        fs::path backup=games / (L"previous-" + std::to_wstring(GetTickCount64()));
        fs::rename(active,backup,ec);
        if (ec) { *error=L"Falha ao preservar instalação anterior."; return false; }
    }
    fs::rename(stage,active,ec);
    if (ec) { *error=L"Falha ao ativar arquivos importados."; return false; }
    return Installed();
}
struct ImportJob { fs::path directory; HWND window; };
static DWORD WINAPI ImportWorker(void* raw) {
    std::unique_ptr<ImportJob> job((ImportJob*)raw);
    std::wstring error;
    const bool ok=ImportPackages(job->directory,&error);
    g_import_error=std::move(error);
    PostMessageW(job->window,kImportFinishedMessage,ok?1:0,0);
    return 0;
}
static void StartNativeGame() {
    if (!Installed()) {
        MessageBoxW(g_main,L"Jogo não preparado.",kTitle,MB_OK|MB_ICONWARNING);
        return;
    }
    const fs::path runtime=g_exe_dir / L"scarlet.exe";
    if (!FileExists(runtime.wstring())) {
        MessageBoxW(g_main,L"scarlet.exe não encontrado.",kTitle,MB_OK|MB_ICONERROR);
        return;
    }
    std::wstring cmd=QuoteArg(runtime.wstring()) + L" --play " + QuoteArg(InstalledRoot().wstring());
    std::vector<wchar_t> args(cmd.begin(),cmd.end());args.push_back(L'\0');
    STARTUPINFOW si{};si.cb=sizeof si;
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(runtime.c_str(),args.data(),nullptr,nullptr,FALSE,0,nullptr,
                        g_exe_dir.c_str(),&si,&pi)) {
        MessageBoxW(g_main,L"Não foi possível iniciar Scarlet.",kTitle,MB_OK|MB_ICONERROR);
        return;
    }
    CloseHandle(pi.hThread);
    AllowSetForegroundWindow(pi.dwProcessId);
    SetWindowTextW(g_main,L"Scarlet — jogo em execução");
    ShowWindow(g_main,SW_MINIMIZE);
    auto* context=new GameWaitContext{pi.hProcess,g_main};
    HANDLE waiter=CreateThread(nullptr,0,WaitForGameProcess,context,0,nullptr);
    if (waiter) CloseHandle(waiter);
    else {delete context;CloseHandle(pi.hProcess);}
}
void LaunchGame() {
    if (g_importing.load()) return;
    SaveSettings();
    const fs::path folder=GetText(g_game_edit);
    auto packages=PackageFiles(folder);
    if (packages.empty()) {
        MessageBoxW(g_main,L"Selecione a pasta com os NSP/XCI.",kTitle,MB_OK|MB_ICONWARNING);
        return;
    }
    if (InstallMatches(packages)) {StartNativeGame(); return;}
    g_importing.store(true);
    RefreshStatus();
    auto* job=new ImportJob{folder,g_main};
    HANDLE thread=CreateThread(nullptr,0,ImportWorker,job,0,nullptr);
    if (thread) CloseHandle(thread);
    else {delete job;g_importing.store(false);MessageBoxW(g_main,L"Falha ao iniciar importação.",kTitle,MB_OK|MB_ICONERROR);}
}


void CreateGamePage() {
    // All labels/status are painted by GDI+ in WM_PAINT. Never redraw
    // transparent STATIC labels over the background (text ghosting bug).
    g_game_edit = MakeEdit(Game,ID_GAME_EDIT,300,186,640,36);
    MakeButton(Game,ID_GAME_BROWSE,955,186,168,36,L"PROCURAR");
    g_dlc_list = CreateWindowExW(WS_EX_CLIENTEDGE,L"LISTBOX",L"",
                  WS_CHILD|WS_VISIBLE|WS_TABSTOP|WS_VSCROLL|
                  LBS_NOTIFY|LBS_NOINTEGRALHEIGHT,
                  300,300,640,212,g_main,(HMENU)ID_DLC_LIST,g_instance,nullptr);
    SendMessageW(g_dlc_list,WM_SETFONT,(WPARAM)g_font,TRUE);
    SetWindowTheme(g_dlc_list,L"DarkMode_Explorer",nullptr);
    AddToPage(Game,g_dlc_list);
    MakeButton(Game,ID_DLC_ADD,955,300,168,42,L"+ ADICIONAR NSP");
    MakeButton(Game,ID_UPDATE_BROWSE,955,353,168,42,L"+ ADICIONAR PASTA");
    MakeButton(Game,ID_DLC_REMOVE,955,406,168,42,L"REMOVER");
}

void CreateGraphicsPage() {
    MakeStatic(Graphics, 300, 102, 700, 34, L"GRÁFICOS", true);

    MakeStatic(Graphics, 300, 160, 260, 24, L"Resolução");
    std::array<const wchar_t*, kResolutions.size()> res_labels{};
    for (size_t i = 0; i < kResolutions.size(); ++i) res_labels[i] = kResolutions[i].label;
    g_resolution = MakeCombo(Graphics, ID_RESOLUTION, 650, 154, 360, 240,
                             res_labels.data(), res_labels.size(), 2);

    MakeStatic(Graphics, 300, 215, 260, 24, L"Modo de exibição");
    g_display_mode = MakeCombo(Graphics, ID_DISPLAY_MODE, 650, 209, 360, 160, kDisplayModes, 1);

    MakeStatic(Graphics, 300, 270, 260, 24, L"Limite de FPS");
    g_fps = MakeCombo(Graphics, ID_FPS, 650, 264, 360, 180, kFpsModes, 1);

    MakeStatic(Graphics, 300, 325, 260, 24, L"Upscaling");
    g_upscaler = MakeCombo(Graphics, ID_UPSCALER, 650, 319, 360, 220, kUpscalers, 0);

    MakeStatic(Graphics, 300, 380, 260, 24, L"Qualidade do upscaling");
    g_quality = MakeCombo(Graphics, ID_UPSCALER_QUALITY, 650, 374, 360, 180,
                          kUpscalerQualities, 0);

    g_frame_generation = MakeCheckbox(Graphics, ID_FRAME_GENERATION, 300, 444, 450, 30,
                                      L"Frame Generation (FSR 3)", false);
    g_async_shaders = MakeCheckbox(Graphics, ID_ASYNC_SHADERS, 300, 488, 450, 30,
                                   L"Shader assíncrono", true);

    MakeStatic(Graphics, 300, 544, 810, 55,
               L"DLSS usa NVIDIA NGX; FSR 3/3.1 e Frame Generation usam FidelityFX Vulkan. "
               L"FSR 4 usa o provider v07 experimental quando os assets compatíveis estiverem instalados.");
}

void CreateControlsPage() {
    MakeStatic(Controls, 300, 102, 700, 34, L"CONTROLES", true);

    MakeStatic(Controls, 300, 164, 300, 24, L"Estilo dos ícones do controle");
    g_controller_style = MakeCombo(Controls, ID_CONTROLLER_STYLE, 650, 158, 360, 180,
                                   kControllerStyles, 0);

    g_auto_controller = MakeCheckbox(Controls, ID_AUTO_CONTROLLER, 300, 224, 540, 30,
                                     L"Configurar automaticamente o primeiro controle conectado", true);

    MakeStatic(Controls, 300, 296, 780, 80,
               L"O Scarlet PC detecta controles automaticamente. Para remapeamento detalhado, "
               L"pressione F12 durante o jogo e use o painel de controles integrado.");

    MakeStatic(Controls, 300, 400, 780, 70,
               L"Perfis visuais: Automático, Xbox, PlayStation e Nintendo. "
               L"A preferência fica salva no launcher para o overlay de controles.");
}

void CreateGeneralPage() {
    MakeStatic(General, 300, 102, 700, 34, L"GERAL", true);

    MakeStatic(General, 300, 164, 260, 24, L"Idioma do launcher");
    g_language = MakeCombo(General, ID_LANGUAGE, 650, 158, 360, 150, kLanguages, 0);

    g_close_on_launch = MakeCheckbox(General, ID_CLOSE_ON_LAUNCH, 300, 224, 560, 30,
                                     L"Fechar o launcher depois de iniciar o jogo", false);

    MakeButton(General, ID_OPEN_USER, 300, 310, 330, 42, L"ABRIR PASTA DO USUÁRIO");
    MakeButton(General, ID_OPEN_LOGS, 650, 310, 330, 42, L"ABRIR LOGS");

    MakeStatic(General, 300, 392, 780, 90,
               L"O launcher salva apenas caminhos e preferências locais em user\\config\\scarlet_launcher.ini. "
               L"Nenhum jogo, DLC, update ou key é incluído no pacote Scarlet PC.");
}

void CreateNavigation() {
    HWND tab = CreateWindowExW(0, L"BUTTON", L"JOGO",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_OWNERDRAW,
                28, 190, 205, 52, g_main, reinterpret_cast<HMENU>(ID_TAB_GAME),
                g_instance, nullptr);
    SendMessageW(tab,WM_SETFONT,reinterpret_cast<WPARAM>(g_font_bold),TRUE);
    HWND play = CreateWindowExW(0, L"BUTTON", L"JOGAR",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_OWNERDRAW,
                1008, 650, 220, 58, g_main,
                reinterpret_cast<HMENU>(ID_PLAY), g_instance, nullptr);
    SendMessageW(play,WM_SETFONT,reinterpret_cast<WPARAM>(g_font_large),TRUE);
}
void CreateUi() {
    CreateNavigation();
    CreateGamePage();
    ShowPage(Game);
}

void DrawButton(const DRAWITEMSTRUCT& dis) {
    wchar_t text[256]{};
    GetWindowTextW(dis.hwndItem, text, 256);

    const int id = static_cast<int>(dis.CtlID);
    const bool pressed = (dis.itemState & ODS_SELECTED) != 0;
    const bool focused = (dis.itemState & ODS_FOCUS) != 0;
    const bool tab = id >= ID_TAB_GAME && id <= ID_TAB_GENERAL;
    const bool active_tab = tab && static_cast<int>(g_page) == (id - ID_TAB_GAME);
    const bool play = id == ID_PLAY;

    COLORREF bg = RGB(38, 29, 33);
    COLORREF border = RGB(180, 143, 42);
    COLORREF fg = RGB(245, 240, 224);

    if (play) {
        bg = pressed ? RGB(125, 18, 18) : RGB(171, 35, 31);
        border = RGB(233, 196, 50);
    } else if (active_tab) {
        bg = RGB(143, 30, 27);
        border = RGB(231, 193, 50);
    } else if (pressed) {
        bg = RGB(68, 43, 45);
    }

    HBRUSH brush = CreateSolidBrush(bg);
    FillRect(dis.hDC, &dis.rcItem, brush);
    DeleteObject(brush);

    HPEN pen = CreatePen(PS_SOLID, (active_tab || play || focused) ? 2 : 1, border);
    HGDIOBJ old_pen = SelectObject(dis.hDC, pen);
    HGDIOBJ old_brush = SelectObject(dis.hDC, GetStockObject(NULL_BRUSH));
    Rectangle(dis.hDC, dis.rcItem.left, dis.rcItem.top, dis.rcItem.right, dis.rcItem.bottom);
    SelectObject(dis.hDC, old_brush);
    SelectObject(dis.hDC, old_pen);
    DeleteObject(pen);

    SetBkMode(dis.hDC, TRANSPARENT);
    SetTextColor(dis.hDC, fg);
    HFONT font = play ? g_font_large : g_font_bold;
    HGDIOBJ old_font = SelectObject(dis.hDC, font);
    RECT text_rect = dis.rcItem;
    DrawTextW(dis.hDC, text, -1, &text_rect, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    SelectObject(dis.hDC, old_font);
}

void DrawBackground(HWND hwnd, HDC hdc) {
    RECT rect{};
    GetClientRect(hwnd, &rect);
    Gdiplus::Graphics graphics(hdc);
    graphics.SetInterpolationMode(InterpolationModeHighQualityBicubic);

    const int width = rect.right - rect.left;
    const int height = rect.bottom - rect.top;

    SolidBrush fallback(Color(255, 94, 13, 16));
    graphics.FillRectangle(&fallback, 0, 0, width, height);

    if (g_background && g_background->GetLastStatus() == Ok) {
        const UINT image_width = g_background->GetWidth();
        const UINT image_height = g_background->GetHeight();
        if (image_width > 0 && image_height > 0) {
            const double scale = std::min(
                static_cast<double>(width) / static_cast<double>(image_width),
                static_cast<double>(height) / static_cast<double>(image_height));
            const int draw_width =
                static_cast<int>(static_cast<double>(image_width) * scale + 0.5);
            const int draw_height =
                static_cast<int>(static_cast<double>(image_height) * scale + 0.5);
            const int draw_x = (width - draw_width) / 2;
            const int draw_y = (height - draw_height) / 2;
            graphics.DrawImage(g_background.get(), draw_x, draw_y, draw_width, draw_height);
        }
    }

    SolidBrush left_panel(Color(220, 16, 10, 16));
    graphics.FillRectangle(&left_panel, 0, 0, 260, height);

    SolidBrush content_panel(Color(220, 17, 14, 20));
    graphics.FillRectangle(&content_panel, 270, 72, width - 300, height - 132);

    Pen gold(Color(230, 222, 181, 46), 2.0f);
    graphics.DrawLine(&gold, 270, 72, width - 30, 72);
    graphics.DrawLine(&gold, 270, height - 60, width - 30, height - 60);

    FontFamily family(L"Segoe UI");
    Gdiplus::Font title_font(&family, 28.0f, FontStyleBold, UnitPixel);
    SolidBrush title_brush(Color(255, 245, 213, 77));
    graphics.DrawString(L"SCARLET PC", -1, &title_font, PointF(28.0f, 94.0f), &title_brush);

    Gdiplus::Font small_font(&family, 13.0f, FontStyleRegular, UnitPixel);
    SolidBrush small_brush(Color(220, 240, 231, 213));
    graphics.DrawString(L"Pokémon Scarlet • Windows", -1, &small_font,
                        PointF(30.0f, 133.0f), &small_brush);
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
    case WM_CREATE:
        g_main = hwnd;
        CreateUi();
        LoadSettings();
        return 0;

    case WM_COMMAND: {
        const int id = LOWORD(wparam);
        switch (id) {
        case ID_TAB_GAME: ShowPage(Game); return 0;
        case ID_TAB_GRAPHICS: ShowPage(Graphics); return 0;
        case ID_TAB_CONTROLS: ShowPage(Controls); return 0;
        case ID_TAB_GENERAL: ShowPage(General); return 0;
        case ID_PLAY: LaunchGame(); return 0;

        case ID_GAME_BROWSE: {
            auto folder=OpenPackageFolder(hwnd);
            if (!folder.empty()) SetText(g_game_edit,folder);
            RefreshStatus();
            return 0;
        }
        case ID_UPDATE_BROWSE: {
            const auto folder=OpenPackageFolder(hwnd);
            if (!folder.empty() && std::find_if(
                g_extra_folders.begin(),g_extra_folders.end(),
                [&](const std::wstring& p){ return Fold(p)==Fold(folder); })
                ==g_extra_folders.end()) {
                g_extra_folders.push_back(folder);
                SaveSettings();
                RefreshStatus();
            }
            return 0;
        }
        case ID_DLC_ADD: {
            const auto file=OpenFile(hwnd,
                L"NSP / XCI\0*.nsp;*.xci\0Todos os arquivos\0*.*\0");
            if (!file.empty() && std::find_if(g_dlcs.begin(),g_dlcs.end(),
                   [&](const std::wstring& p){ return Fold(p)==Fold(file); })
                   ==g_dlcs.end()) {
                g_dlcs.push_back(file);
                SaveSettings();
                RefreshStatus();
            }
            return 0;
        }
        case ID_DLC_REMOVE: {
            const int selected=(int)SendMessageW(g_dlc_list,LB_GETCURSEL,0,0);
            if (selected<0 || (size_t)selected>=g_visible_packages.size()) return 0;
            auto item=g_visible_packages[(size_t)selected];
            if (item.kind==1 && item.index<g_dlcs.size())
                g_dlcs.erase(g_dlcs.begin()+item.index);
            else if (item.kind==2 && item.index<g_extra_folders.size())
                g_extra_folders.erase(g_extra_folders.begin()+item.index);
            else return 0; // files from the primary directory are not removable
            SaveSettings();
            RefreshStatus();
            return 0;
        }
        case ID_OPEN_USER:
            OpenFolder(g_exe_dir / L"user");
            return 0;
        case ID_OPEN_LOGS:
            OpenFolder(g_exe_dir / L"user" / L"log");
            return 0;
        default:
            break;
        }
        if (HIWORD(wparam) == EN_CHANGE && id == ID_GAME_EDIT) {
            RefreshStatus();
        }
        break;
    }

    case WM_DRAWITEM:
        DrawButton(*reinterpret_cast<DRAWITEMSTRUCT*>(lparam));
        return TRUE;

    case WM_CTLCOLORSTATIC: {
        HDC dc = reinterpret_cast<HDC>(wparam);
        SetTextColor(dc, RGB(244, 238, 226));
        SetBkMode(dc, TRANSPARENT);
        return reinterpret_cast<LRESULT>(GetStockObject(NULL_BRUSH));
    }
    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORLISTBOX: {
        HDC dc = reinterpret_cast<HDC>(wparam);
        SetTextColor(dc, RGB(244, 238, 226));
        SetBkColor(dc, RGB(30, 25, 31));
        return reinterpret_cast<LRESULT>(g_edit_brush);
    }

    case WM_ERASEBKGND:
        return 1;

    case WM_PAINT: {
        PAINTSTRUCT ps{};
        HDC dc = BeginPaint(hwnd, &ps);
        DrawBackground(hwnd, dc);
        EndPaint(hwnd, &ps);
        return 0;
    }

    case kImportFinishedMessage: {
        g_importing.store(false);
        RefreshStatus();
        if (wparam) StartNativeGame();
        else MessageBoxW(hwnd,
             g_import_error.empty()?L"Falha na importação.":g_import_error.c_str(),
             kTitle,MB_OK|MB_ICONERROR);
        return 0;
    }
    case WM_TIMER:
        if (g_importing.load()) {
            g_status_text=L"Preparando arquivos...";
            RECT r{300,529,1125,600};
            InvalidateRect(hwnd,&r,FALSE);
        }
        return 0;
    case kGameExitedMessage: {
        const DWORD code = static_cast<DWORD>(wparam);
        SetWindowTextW(hwnd, kTitle);
        ShowWindow(hwnd, SW_RESTORE);
        SetForegroundWindow(hwnd);

        if (code != 0) {
            std::wstring message = L"Pokémon Scarlet foi encerrado inesperadamente.\nCódigo do processo: " +
                                   std::to_wstring(static_cast<LONG>(code));
            if (code == 0xC0000005u) {
                message += L"\n\n0xC0000005: access violation no runtime/driver.";
            }
            message += L"\n\nAbra a aba GERAL > ABRIR LOGS para o diagnóstico.";
            MessageBoxW(hwnd, message.c_str(), L"Scarlet — jogo encerrado", MB_OK | MB_ICONERROR);
        }
        return 0;
    }

    case WM_CLOSE:
        SaveSettings();
        DestroyWindow(hwnd);
        return 0;

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

} // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int show) {
    g_instance = instance;
    // Required by modern Shell folder dialogs (BIF_NEWDIALOGSTYLE).
    HRESULT com = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    INITCOMMONCONTROLSEX controls{sizeof(controls), ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES};
    InitCommonControlsEx(&controls);

    GdiplusStartupInput gdiplus_input;
    if (GdiplusStartup(&g_gdiplus_token, &gdiplus_input, nullptr) != Ok) return 1;

    g_exe_dir = ExeDir();
    g_ini_path = g_exe_dir / L"user" / L"config" / L"scarlet_launcher.ini";
    const fs::path background = g_exe_dir / L"assets" / L"scarlet_launcher_background.jpg";
    if (fs::is_regular_file(background)) {
        // GDI+ Image(path) keeps the source file open for the lifetime of the Image.
        // Clone it immediately so setup/packaging can replace the background while
        // the launcher is running.
        Image file_image(background.c_str());
        if (file_image.GetLastStatus() == Ok) {
            g_background.reset(file_image.Clone());
        }
    }

    g_edit_brush = CreateSolidBrush(RGB(30, 25, 31));
    g_panel_brush = CreateSolidBrush(RGB(20, 16, 21));

    g_font = CreateFontW(-17, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                         OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                         DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
    g_font_bold = CreateFontW(-17, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                              OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                              DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
    g_font_large = CreateFontW(-24, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                               OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                               DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hIcon = LoadIconW(instance, MAKEINTRESOURCEW(1));
    if (!wc.hIcon) wc.hIcon = LoadIconW(nullptr, IDI_APPLICATION);
    wc.hIconSm = wc.hIcon;
    wc.lpszClassName = kWindowClass;
    wc.style = CS_HREDRAW | CS_VREDRAW;
    RegisterClassExW(&wc);

    RECT window_rect{0, 0, kWindowWidth, kWindowHeight};
    AdjustWindowRectEx(&window_rect, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                       FALSE, 0);

    HWND hwnd = CreateWindowExW(
        0, kWindowClass, kTitle,
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT,
        window_rect.right - window_rect.left, window_rect.bottom - window_rect.top,
        nullptr, nullptr, instance, nullptr);

    if (!hwnd) return 2;

    BOOL dark = TRUE;
    DwmSetWindowAttribute(hwnd, 20, &dark, sizeof(dark));

    ShowWindow(hwnd, show);
    SetTimer(hwnd,1,750,nullptr);
    UpdateWindow(hwnd);

    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    if (g_font) DeleteObject(g_font);
    if (g_font_bold) DeleteObject(g_font_bold);
    if (g_font_large) DeleteObject(g_font_large);
    if (g_edit_brush) DeleteObject(g_edit_brush);
    if (g_panel_brush) DeleteObject(g_panel_brush);
    g_background.reset();
    GdiplusShutdown(g_gdiplus_token);
    if (SUCCEEDED(com)) CoUninitialize();
    return static_cast<int>(msg.wParam);
}
