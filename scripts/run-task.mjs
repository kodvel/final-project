import { spawnSync } from 'node:child_process'

const task = process.argv[2]

const taskMap = {
  dev: ['dev'],
  build: ['build'],
  test: ['test'],
  lint: ['lint'],
  format: ['format'],
  check: ['lint', 'test', 'build'],
}

const tasks = taskMap[task]

if (!tasks) {
  console.error(`Unknown task: ${task}`)
  process.exit(1)
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    shell: process.platform === 'win32',
    ...options,
  })

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

function hasGitHead() {
  const result = spawnSync('git', ['rev-parse', '--verify', 'HEAD'], {
    stdio: 'ignore',
  })

  return result.status === 0
}

function runMoon() {
  const targets = tasks.map((item) => `:${item}`)
  const args = task === 'format' || task === 'dev' ? ['run', ...targets] : ['run', '--force', ...targets]

  run('moon', args)
}

function runFallback() {
  if (task === 'dev') {
    run('pnpm', ['--parallel', '--filter', '@final-project/web', '--filter', '@final-project/api', 'dev'])
    return
  }

  const projects = ['@final-project/web', '@final-project/api']

  for (const item of tasks) {
    for (const project of projects) {
      run('pnpm', ['--filter', project, item])
    }
  }
}

if (hasGitHead()) {
  runMoon()
} else {
  console.warn('No git HEAD found; running direct pnpm project tasks until the first commit exists.')
  runFallback()
}
