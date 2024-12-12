package util

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"net/url"
	"net/http"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/cognitoidentityprovider"
	"github.com/aws/aws-sdk-go-v2/service/cognitoidentityprovider/types"
	awshttp "github.com/aws/aws-sdk-go-v2/aws/transport/http"
)

// Types
type User struct {
	Name string
	Uid  uint64
}

type Group struct {
	Name string
	Gid  uint64
}

// Interface that is used to determine identity. This set of functions is used
// by NSS. By implementing this as an interface, a mock can be provided during
// testing which adheres to the same contract.
type IdentityProvider interface {
	GetAllUsers() ([]User, error)
	GetUser(name string) (User, error)
	GetUserGroups(user User) ([]Group, error)
	GetAllGroups() ([]Group, error)
}

// This is the specific provider for Cognito. It is constructed with a "config"
// which will provide the specific values (e.g. like User Pool Id) that are
// needed during operation.
type CognitoIdentityProvider struct {
	Config map[string]string
}

// Interface that is used for authentication. This function is used by PAM
type AuthProvider interface {
	AuthenticateUser(username string, password string) (bool, error)
}

// The specific provider for Cognito.
type CognitoAuthProvider struct {
	Config map[string]string
}

// Helper functions

// awsConfig() loads the credentials from either the file on the system or from
// the provider chain (e.g. profiles, env, IMDS) if they are empty in the
// config file.
func awsConfig(auth_config map[string]string) (aws.Config, error) {

	region, exists := auth_config["aws_region"]
	if !exists {
		return aws.Config{}, fmt.Errorf("Unable to determine the AWS region.")
	}

	// Retrieve values from the config
	accessKeyId, exists := auth_config["aws_access_key_id"]
	if !exists {
		return aws.Config{}, fmt.Errorf("Unable to determine the AWS Secret Access Key.")
	}

	secretAccessKey, exists := auth_config["aws_secret_access_key"]
	if !exists {
		return aws.Config{}, fmt.Errorf("Unable to determine the AWS Secret Access Key.")
	}

	sessionToken, exists := auth_config["aws_session_token"]
	if !exists {
		sessionToken = ""
	}

	const ec2MetadataIP = "169.254.169.254"

	var httpClient *awshttp.BuildableClient
	if httpsProxy, exists := auth_config["https_proxy"]; exists {
		proxyURL, err := url.Parse(httpsProxy)
		if err != nil {
			return aws.Config{}, fmt.Errorf("Unable to parse HTTPS proxy URL: %v", err)
		}
		httpClient = awshttp.NewBuildableClient().WithTransportOptions(func(tr *http.Transport) {
			tr.Proxy = func(r *http.Request) (*url.URL, error) {
				if r.URL.Host == ec2MetadataIP { // AWS EC2 instance metadata service
					return nil, nil // No Proxy for IMDS
				}
				return http.ProxyURL(proxyURL)(r)
			}
		})
	} else {
		httpClient = awshttp.NewBuildableClient()
	}

	if accessKeyId != "" {
		// Set credentials
		creds := credentials.NewStaticCredentialsProvider(accessKeyId, secretAccessKey, sessionToken)

		// Create the cfg with static credentials
		cfg, err := config.LoadDefaultConfig(
			context.TODO(),
			config.WithCredentialsProvider(creds),
			config.WithRegion(region),
			config.WithHTTPClient(httpClient),
		)

		if err != nil {
			return aws.Config{}, fmt.Errorf("Unable to load the AWS SDK config")
		}
		return cfg, nil
	} else {
		// Try to create the config with default credentials
		cfg, err := config.LoadDefaultConfig(context.TODO(),
			config.WithRegion(region),
			config.WithHTTPClient(httpClient),
		)
		if err != nil {
			return aws.Config{}, fmt.Errorf("Unable to load the AWS SDK config")
		}
		return cfg, nil
	}
}

func getUserUid(config map[string]string, attributes []types.AttributeType) (uint64, error) {
	var uid uint64
	uidAttribute, exists := config["cognito_uid_attribute"]
	if !exists {
		return uid, fmt.Errorf("Unable to determine the Cognito UID Attribute.")
	}

	for _, attr := range attributes {
		if *attr.Name == uidAttribute {
			return strconv.ParseUint(*attr.Value, 10, 64)
		}
	}
	return uid, fmt.Errorf("Unable to find Cognito UID Attribute %s", uidAttribute)
}

// Public interface for getting users and groups

func (idp CognitoIdentityProvider) GetUser(username string) (User, error) {
	userPoolId, exists := idp.Config["user_pool_id"]
	if !exists {
		return User{}, fmt.Errorf("Unable to determine the Cognito User Pool ID.")
	}

	cfg, err := awsConfig(idp.Config)
	if err != nil {
		return User{}, err
	}

	svc := cognitoidentityprovider.NewFromConfig(cfg)

	params := &cognitoidentityprovider.AdminGetUserInput{
		UserPoolId: aws.String(userPoolId),
		Username:   aws.String(username),
	}

	result, err := svc.AdminGetUser(context.TODO(), params)
	if err != nil {
		return User{}, err
	}

	uid, err := getUserUid(idp.Config, result.UserAttributes)
	if err != nil {
		return User{}, err
	}

	user := User{*result.Username, uid}

	return user, nil
}

func (idp CognitoIdentityProvider) GetAllUsers() ([]User, error) {
	userPoolId, exists := idp.Config["user_pool_id"]
	if !exists {
		return nil, fmt.Errorf("Unable to determine the Cognito User Pool ID.")
	}

	cfg, err := awsConfig(idp.Config)
	if err != nil {
		return nil, err
	}

	svc := cognitoidentityprovider.NewFromConfig(cfg)

	var nextToken *string
	var users []User

	for {
		params := &cognitoidentityprovider.ListUsersInput{
			UserPoolId: aws.String(userPoolId),
			Limit:      aws.Int32(60),
			Filter:     aws.String("cognito:user_status = \"CONFIRMED\""),
		}

		if nextToken != nil {
			params.PaginationToken = nextToken
		}

		result, err := svc.ListUsers(context.TODO(), params)
		if err != nil {
			return nil, err
		}

		for _, user := range result.Users {
			uid, err := getUserUid(idp.Config, user.Attributes)
			if err != nil {
				return nil, err
			}

			users = append(users, User{*user.Username, uid})
		}

		// Update pagination token for next page
		nextToken = result.PaginationToken

		// Exit if no more pages left
		if nextToken == nil {
			break
		}
	}

	return users, nil
}

func (idp CognitoIdentityProvider) GetUserGroups(user User) ([]Group, error) {
	userPoolId, exists := idp.Config["user_pool_id"]
	if !exists {
		return nil, fmt.Errorf("Unable to determine the Cognito User Pool ID.")
	}

	cfg, err := awsConfig(idp.Config)
	if err != nil {
		return nil, err
	}

	svc := cognitoidentityprovider.NewFromConfig(cfg)

	params := &cognitoidentityprovider.AdminListGroupsForUserInput{
		Username:   aws.String(user.Name),
		UserPoolId: aws.String(userPoolId),
	}

	result, err := svc.AdminListGroupsForUser(context.TODO(), params)
	if err != nil {
		return nil, err
	}

	cognitoGroups := (*result).Groups
	var groups []Group

	// Sort the groups by precedence
	sort.Slice(cognitoGroups, func(i, j int) bool {
		return *cognitoGroups[i].Precedence < *cognitoGroups[j].Precedence
	})

	for _, group := range cognitoGroups {

		gid, err := GetGroupHash(idp.Config, *group.GroupName)
		if err != nil {
			return nil, err
		}

		groups = append(groups, Group{*group.GroupName, gid})
	}

	// Add default group
	gid, err := GetGroupHash(idp.Config, idp.Config["cognito_default_user_group"])
	if err != nil {
		return nil, err
	}
	groups = append(groups, Group{idp.Config["cognito_default_user_group"], gid})

	return groups, nil
}

func (idp CognitoIdentityProvider) GetAllGroups() ([]Group, error) {
	userPoolId, exists := idp.Config["user_pool_id"]
	if !exists {
		return nil, fmt.Errorf("Unable to determine the Cognito User Pool ID.")
	}

	cfg, err := awsConfig(idp.Config)
	if err != nil {
		return nil, err
	}

	svc := cognitoidentityprovider.NewFromConfig(cfg)

	params := &cognitoidentityprovider.ListGroupsInput{
		UserPoolId: aws.String(userPoolId),
	}

	result, err := svc.ListGroups(context.TODO(), params)
	if err != nil {
		return nil, err
	}

	var groups []Group
	for _, group := range result.Groups {

		gid, err := GetGroupHash(idp.Config, *group.GroupName)
		if err != nil {
			return nil, err
		}

		groups = append(groups, Group{*group.GroupName, gid})
	}

	return groups, nil
}

// Public interface for authenticating against Cognito Identity Provider

func (ap CognitoAuthProvider) AuthenticateUser(username string, password string) (bool, error) {
	userPoolId, exists := ap.Config["user_pool_id"]
	if !exists {
		return false, fmt.Errorf("Unable to determine the Cognito User Pool ID.")
	}

	clientId, exists := ap.Config["client_id"]
	if !exists {
		return false, fmt.Errorf("Unable to determine the Cognito Client ID.")
	}

	cfg, err := awsConfig(ap.Config)
	if err != nil {
		return false, err
	}

	svc := cognitoidentityprovider.NewFromConfig(cfg)

	params := &cognitoidentityprovider.AdminInitiateAuthInput{
		UserPoolId: aws.String(userPoolId),
		ClientId:   aws.String(clientId),
		AuthFlow:   types.AuthFlowTypeAdminNoSrpAuth,
		AuthParameters: map[string]string{
			"USERNAME": username,
			"PASSWORD": password,
		},
	}

	_, err = svc.AdminInitiateAuth(context.TODO(), params)
	if err != nil {
		return false, err
	}

	return true, nil
}
