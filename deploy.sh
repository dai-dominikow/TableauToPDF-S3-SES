export ENV="${EnvStageName:=dev}"
export REGION="${Region:=us-west-2}"
export CODE_PIPELINE_BUCKET="$ENV-airtm-code-pipeline"
export STACK_NAME="dragonite"

sam build \
--use-container \
--parameter-overrides "ParameterKey=EnvStageName,ParameterValue=$ENV ParameterKey=Region,ParameterValue=$REGION"

sam package \
--output-template-file packaged.yaml \
--s3-bucket $CODE_PIPELINE_BUCKET

sam deploy \
--template-file packaged.yaml \
--stack-name $STACK_NAME \
--region $REGION \
--capabilities CAPABILITY_AUTO_EXPAND \
--parameter-overrides "ParameterKey=EnvStageName,ParameterValue=$ENV ParameterKey=Region,ParameterValue=$REGION"
