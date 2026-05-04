(function () {
    function getContentRoot() {
        var html = document.documentElement;
        if (html) {
            var contentRoot = html.getAttribute("data-content_root");
            if (contentRoot) {
                return contentRoot;
            }
        }

        if (html && html.dataset && html.dataset.contentRoot) {
            return html.dataset.contentRoot;
        }

        if (
            window.DOCUMENTATION_OPTIONS &&
            typeof window.DOCUMENTATION_OPTIONS.URL_ROOT === "string" &&
            window.DOCUMENTATION_OPTIONS.URL_ROOT
        ) {
            return window.DOCUMENTATION_OPTIONS.URL_ROOT;
        }

        return null;
    }

    function getEmbeddedPayload(scriptId) {
        var script = document.getElementById(scriptId);
        if (!script || !script.textContent) {
            return null;
        }

        try {
            return JSON.parse(script.textContent);
        } catch (error) {
            return null;
        }
    }

    function normalizePathname(pathname) {
        return pathname.endsWith("/") ? pathname : pathname + "/";
    }

    function getVersionSegment(pathname) {
        var marker = "/docs/";
        var index = pathname.indexOf(marker);
        if (index === -1) {
            return null;
        }

        var remainder = pathname.slice(index + marker.length);
        var version = remainder.split("/")[0];
        return version || null;
    }

    function getVersionRootFromPath() {
        var marker = "/docs/";
        var pathname = window.location.pathname;
        var index = pathname.indexOf(marker);
        var version = getVersionSegment(pathname);
        if (index === -1 || !version) {
            return null;
        }

        return new URL(pathname.slice(0, index + marker.length) + version + "/", window.location.href);
    }

    function getVersionRoot() {
        var pathVersionRoot = getVersionRootFromPath();
        var pathVersion = getVersionSegment(window.location.pathname);
        var contentRoot = getContentRoot();
        if (!contentRoot) {
            return pathVersionRoot;
        }

        var metadataVersionRoot = new URL(contentRoot, window.location.href);
        var metadataVersion = getVersionSegment(metadataVersionRoot.pathname);
        if (pathVersionRoot && pathVersion && metadataVersion !== pathVersion) {
            return pathVersionRoot;
        }

        return metadataVersionRoot;
    }

    function detectCurrentVersion(versions, siteRoot) {
        var pathname = normalizePathname(window.location.pathname);

        for (var i = 0; i < versions.length; i += 1) {
            var versionPath = normalizePathname(new URL(versions[i].path, siteRoot).pathname);
            if (pathname === versionPath || pathname.indexOf(versionPath) === 0) {
                return versions[i];
            }
        }

        return null;
    }

    function buildTargetUrl(siteRoot, currentVersionRoot, nextVersion) {
        var currentPage = new URL(window.location.href);
        var relativePath = currentPage.pathname.slice(currentVersionRoot.pathname.length);
        var targetRoot = new URL(nextVersion.path, siteRoot);
        var targetPath = relativePath || "index.html";
        var targetUrl = new URL(targetPath, targetRoot);

        targetUrl.hash = currentPage.hash;
        targetUrl.search = currentPage.search;
        return targetUrl;
    }

    async function initVersionSwitcher() {
        var container = document.getElementById("version-switcher");
        var select = document.getElementById("version-select");
        var currentVersionRoot = getVersionRoot();

        if (!container || !select || !currentVersionRoot) {
            return;
        }

        var payload = getEmbeddedPayload("versions-data");
        var siteRoot = new URL("../", currentVersionRoot);
        if (!payload) {
            var versionsUrl = new URL("../versions.json", currentVersionRoot);
            var response = await fetch(versionsUrl);
            if (!response.ok) {
                return;
            }

            payload = await response.json();
            siteRoot = new URL("./", versionsUrl);
        }

        var versions = Array.isArray(payload.versions) ? payload.versions : [];
        if (versions.length < 2) {
            return;
        }

        var currentVersion = detectCurrentVersion(versions, siteRoot);
        select.textContent = "";

        versions.forEach(function (version) {
            var option = document.createElement("option");
            option.value = version.name;
            option.textContent = version.name === payload.latest ? version.name + " (latest)" : version.name;
            if (currentVersion && currentVersion.name === version.name) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        if (select.dataset.thornforgeBound !== "true") {
            select.addEventListener("change", function (event) {
                var nextVersion = versions.find(function (version) {
                    return version.name === event.target.value;
                });

                if (!nextVersion) {
                    return;
                }

                var targetUrl = buildTargetUrl(siteRoot, currentVersionRoot, nextVersion);
                window.location.assign(targetUrl.toString());
            });
            select.dataset.thornforgeBound = "true";
        }

        container.hidden = false;
    }

    function start() {
        initVersionSwitcher().catch(function () {
            /* Ignore version switcher failures so the docs still render. */
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
}());
