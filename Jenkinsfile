#!groovy

pipeline {
  agent none

  options {
    disableConcurrentBuilds()
  }

  stages {
    stage('Build Docker image') {
      agent any
      steps {
        script {
          def dockerRepoName = 'zooniverse/hamlet'
          def dockerImageName = "${dockerRepoName}:${BRANCH_NAME}"
          def newImage = docker.build(dockerImageName)
          newImage.push()
          newImage.push('${GIT_COMMIT}')

          if (BRANCH_NAME == 'master') {
            stage('Update latest tag') {
              newImage.push('latest')
            }
          }
        }
      }
    }
    stage('Dry run deployments') {
      agent any
      steps {
        sh "sed 's/__IMAGE_TAG__/${GIT_COMMIT}/g' kubernetes/deployment.tmpl | kubectl --context azure apply --dry-run=client --record -f -"
      }
    }

    stage('Deploy to Kubernetes') {
      when { branch 'master' }
      agent any
      steps {
        sh "sed 's/__IMAGE_TAG__/${GIT_COMMIT}/g' kubernetes/deployment.tmpl | kubectl --context azure apply --record -f -"
      }
    }
  }
}
