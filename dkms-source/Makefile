KERNELRELEASE ?= $(shell uname -r)

.PHONY: clean
clean:
	$(MAKE) -C /lib/modules/$(KERNELRELEASE)/build M=$(CURDIR)/intel/boards clean
