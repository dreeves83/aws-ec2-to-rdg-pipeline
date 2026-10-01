pipeline {
    agent any
    options { 
        timeout(time: 10, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '100'))
    }
	environment {
        YAML_FILE = './config/env_parameters.yml'
        PYTHON_FILE = './ec2_to_rdg.py'
    }
    parameters {
        choice(name: 'ENVIRONMENT', choices: ['qa', 'uat', 'prod'], description: 'AWS account for EC2 instances')
        choice(name: 'AWS_REGION', choices: ['us-east-1', 'us-west-2'], description: 'AWS region for EC2 instances')
        string(name: 'REPO_BRANCH', defaultValue: 'master', description: 'Name of git branch to use')
    }

    stages {
        stage('Create AWS EC2 RDG file') {
            steps {
                script {
					currentBuild.displayName = "#${BUILD_NUMBER}_${ENVIRONMENT}_${AWS_REGION}"
					
					def envParameters = readYaml file: "${YAML_FILE}"
					def ENV_PARAMETERS = envParameters["${AWS_REGION}"]["${ENVIRONMENT}"]
					
					withAWS(role: "${ENV_PARAMETERS['DeploymentRole']}", roleAccount: "${ENV_PARAMETERS['AwsAccount']}", duration: 10800, region: "${AWS_REGION}") {
						awsEc2ToRdg = sh(script: "python3 ${PYTHON_FILE} ${AWS_REGION} ${ENVIRONMENT}", returnStdout: true)
						def awsEc2ToRdgSplit = awsEc2ToRdg.split('---SPLIT---')
						println(awsEc2ToRdgSplit[0])
						def rdgFileName = awsEc2ToRdgSplit[1].trim()
						archiveArtifacts artifacts: "${rdgFileName}", allowEmptyArchive: true
					}
                }
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}
