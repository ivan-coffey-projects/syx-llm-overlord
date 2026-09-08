package syx.llm.overlord;

import game.VERSION;
import game.save.GameLoader;
import game.save.SaveFile;
import init.error.ErrorHandler;
import init.paths.PATHS;
import init.paths.PATHS.PATHS_BASE;
import init.settings.S;
import init.text.D;
import launcher.LSettings;
import menu.Menu;
import snake2d.CORE;
import snake2d.LOG;
import snake2d.PreLoader;

/**
 * Agent-safe game entry: skip SOS Launcher UI and main-menu Continue click.
 *
 * Boots the same way as {@code init.MainProcess}, then loads the newest save
 * (same pick as the Continue button). Falls back to the normal menu if there
 * are no saves.
 *
 * Launch (sandbox / overnight):
 * <pre>
 *   jre/bin/java ... -cp SongsOfSyx.jar:base/script/002_LLM_Overlord.jar \
 *     syx.llm.overlord.AutoContinueMain
 * </pre>
 */
public final class AutoContinueMain {

    private AutoContinueMain() {}

    public static void main(String[] args) {
        PreLoader.load(VERSION.VERSION_STRING, PATHS_BASE.PRELOADER, PATHS_BASE.ICON_FOLDER + "Icon64.png");
        CORE.init(new ErrorHandler());

        LOG.ln("*******************************");
        LOG.ln("* GAME " + VERSION.VERSION_STRING + " (AutoContinue)");
        LOG.ln("*******************************");

        LSettings settings = new LSettings();
        String lang = settings.lang.get();
        PATHS.init(
                settings.mods.get(),
                lang != null && lang.length() > 0 ? lang : null,
                settings.easy.get() == 1);
        D.init();

        SaveFile[] saves = SaveFile.list();
        if (saves.length == 0) {
            LOG.ln("[AutoContinue] no saves — falling back to Menu.start()");
            Menu.start();
            return;
        }

        SaveFile newest = saves[0];
        LOG.ln("[AutoContinue] loading newest save: " + newest.fullName);

        CORE.create(S.get().make());
        CORE.getInput().getMouse().showCusor(false);
        // GameLoader is a CORE_STATE.Constructor — same path as Continue.
        CORE.start(new GameLoader(newest.path));
    }
}
