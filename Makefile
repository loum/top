PY=/usr/bin/env python
NOSE=/usr/bin/nosetests -s -v
GIT=/usr/bin/git

# The TEST variable can be set to allow you to control which tests
# to run.  For example, if the current project has a test set defined at
# "tests/test_<name>.py", to run the "Test<class_name>" class:
#
# $ make test TEST=tests:Test<class_name>
#
# To run individual test cases within each test class:
#
# $ make test TEST=tests:Test<class_name>.test_<test_name>
#
# Note: for this to work you will need to import the test class into
# the current namespace via "tests/__init__.py"
TEST=nparcel.tests:TestLoader \
	 nparcel.tests:TestLoaderIpec \
	 nparcel.tests:TestParser \
	 nparcel.tests:TestDbSession \
	 nparcel.tests:TestReporter \
	 nparcel.tests:TestEmailer \
	 nparcel.tests:TestRest \
	 nparcel.tests:TestRestEmailer \
	 nparcel.tests:TestSmser \
	 nparcel.tests:TestLoaderDaemon \
	 nparcel.tests:TestExporter \
	 nparcel.tests:TestExporterIpec \
	 nparcel.tests:TestConfig \
	 nparcel.tests:TestFtp \
	 nparcel.table.tests:TestAgent \
	 nparcel.table.tests:TestJob \
	 nparcel.table.tests:TestJobItem \
	 nparcel.table.tests:TestTable \
	 nparcel.table.tests:TestIdentityType

sdist:
	$(PY) setup.py sdist

rpm:
	$(PY) setup.py bdist_rpm

docs:
	sphinx-build -b html nparcel/doc/source nparcel/doc/build

test:
	$(NOSE) $(TEST)

clean:
	$(GIT) clean -xdf

.PHONY: test
