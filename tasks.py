from invoke import run, task


@task
def git_push():
    run('git push origin --all')


@task
def pypi():
    run('python setup.py sdist bdist_wheel')


@task
def pypi_upload():
    run('python setup.py sdist bdist_wheel upload')
