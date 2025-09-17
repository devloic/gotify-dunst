ifeq ($(PREFIX),)
    PREFIX := /usr
endif

install:
	# systemd file
	install -d $(DESTDIR)$(PREFIX)/lib/systemd/user/
	install gotify-dunst.service $(DESTDIR)$(PREFIX)/lib/systemd/user/

	# files in /usr/lib
	install -d $(DESTDIR)$(PREFIX)/lib/gotify-dunst/
	install main.py $(DESTDIR)$(PREFIX)/lib/gotify-dunst/
	mkdir -p $(HOME)/.config/gotify-dunst
	test -f $(HOME)/.config/gotify-dunst/gotify-dunst.conf || \
            install -m 644 gotify-dunst.conf $(HOME)/.config/gotify-dunst/gotify-dunst.conf

	# files in /usr/share
	install -d $(DESTDIR)$(PREFIX)/share/applications
	install gotify-dunst.desktop $(DESTDIR)$(PREFIX)/share/applications
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
	install gotify-16.png $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/gotify.png
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/32x32/apps/
	install gotify-32.png $(DESTDIR)$(PREFIX)/share/icons/hicolor/32x32/apps/gotify.png
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/96x96/apps/
	install gotify-96.png $(DESTDIR)$(PREFIX)/share/icons/hicolor/96x96/apps/gotify.png
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
	install gotify-128.png $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/gotify.png
