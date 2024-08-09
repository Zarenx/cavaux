#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            // CBA
            "cba_ui",
            "cba_xeh",
            "cba_jr"
        };
        author = CSTRING(modteam);
        authors[] = {"Brostrom.A (Evul)"};
        url = CSTRING(URL);
        VERSION_CONFIG;
    };
};

class CfgMods {
    class PREFIX {
        dir = "@cavaux";
        name = CSTRING(Name);
        picture = "A3\Ui_f\data\Logos\arma3_expansion_alpha_ca";
        hidePicture = "true";
        hideName = "true";
        actionName = CSTRING(Website);
        action = CSTRING(Url);
        description = CSTRING(Description);
    };
};

#include "CfgSettings.hpp"