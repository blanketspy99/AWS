#!/usr/bin/env python
"""
This script is intended to create snapshots of all the EBS Volumes attached to this instance 
	and delete the old snapshots with a default period of 7 days unless specified.'
Running this script as plain root will take the INSTANCE_PROFILE role of the current instance Cloud Environment (CE)

To run this script as unified for different cloud environment, make sure the AWS STS Token is present as the environment variable
	however you need to alter the function getPresentInstanceID() and getPresentInstanceRegion() to pass the region and instance id
	
Arguments:
	'-i','--Instance-id', help='EBS volume ID', required=True) ##Uncomment this to use different instance-id
    '-d','--delete-old', help='Delete old snapshots? True/False', required=False, type=bool,default=True)
    '-x','--expiry-days', help='Number of days to keep snapshots. Default=7', required=False, type=int, default=7)
	
Usage:
		./ebsSnapshotOfCurrentEC2instance.py  -> Create snapshot of the volumes attached to the instance and delete snaps older than default 7 days.
		./ebsSnapshotOfCurrentEC2instance.py -x 3 -> Create snapshot of the volumes attached to the instance and delete snaps older than 3 days.
		./ebsSnapshotOfCurrentEC2instance.py -d False -> Only create the snapshots of the volumes attached to instance.
"""
import argparse
import subprocess
import json
import logging
import time, datetime, dateutil.parser
#profile = 'backup'
#region = 'eu-west-1'
Tag={'Key':'Group','Value':'backup_PC'} #Tag is used to identify the snapshots backups.
__author__ = 'Shahrukh, Shaik'
__version__ = '1.0.3'
__copyright__ = ''
__maintainer__ = ''
__email__ = ''
__status__ = 'Production'



def bash(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
    return process.communicate()[0].decode('utf-8')
def getOurSnapshots():
	"""
	Return a list of snapshot Dicts created with this plugin.
	"""
	query = "aws ec2 describe-snapshots \
				--filters Name=tag-key,Values={Key} \
				Name=tag-value,Values={Value} --output=json --region {region}".format(region=getPresentInstanceRegion(),**Tag)
	return json.loads(bash(query))['Snapshots']

def createSnapshots(volumeIds):
	"""
	Return True if snapshots of the given volumes are created, else False
	
	Keyword arguments:
	volumeIds -- List of EBS volume IDs
	"""
	# Create the snapshots
	snapshots = []
	for volumeId in volumeIds:
		snapshots.append(createSnapshotForVolume(volumeId))
	
	# Add Name and Group tags to the snapshot
	if len(snapshots):
		snapshotIds = []
		date = time.strftime("%Y-%m-%d")
		return True
	else:
		return False

def createSnapshotForVolume(volumeId):
	"""
	Return a Dict of a created snapshot for the given EBS volume
	
	Keyword arguments:
	volumeId -- An EBS volume ID
	"""
	
	date = time.strftime("%Y-%m-%d")
	message = "Creating snapshot for volume "+"-".join(volumeId)+"..."
	Tags="[{{Key={Key},Value={Value}}}]".format(**Tag)
	print(Tags)
	Description = "'Volume Snapshot {desc}'".format(desc="-".join(volumeId)+"..."+date)
	query = "aws ec2 create-snapshot --volume-id {volId} \
			--description {desc} --tag-specifications 'ResourceType=snapshot,Tags={tags}' \
			--region {region} --output=json".format(volId=volumeId[0],desc=Description,tags=Tags,region=getPresentInstanceRegion())
	print(query)
	response = json.loads(bash(query))
	message += response['SnapshotId']
	logging.info(message)
	
	return response

def deleteOldSnapshots(snapshots, max_age):
	"""
	Delete all listed snapshots older than max_age
	"""
	snapshotIds = []
	date = datetime.datetime.now()
	
	for snapshot in snapshots:
		snapshotDate = dateutil.parser.parse(snapshot['StartTime']).replace(tzinfo=None)
		dateDiff = date - snapshotDate
		#To use hours for retention.
		#hours = divmod(dateDiff.total_seconds(), 3600)[0]
		#if hours >= max_age:
	
		if dateDiff.days >= max_age:
			message = "Deleting snapshot "+snapshot['SnapshotId']+" ("+str(dateDiff.days)+" days old)..."
			# delete-snapshot no longer returns any output
			query = "aws ec2 delete-snapshot \
				--snapshot-id {snapId} --region {region} \
				--output=json".format(snapId=snapshot['SnapshotId'],region=getPresentInstanceRegion())
			bash(query)
	
			message += "done"
			logging.info(message)

def getInstanceVolumeIds(InstanceId):

	"""
	Lists all the volumes attached to an Instance
	"""
	query="aws ec2 describe-volumes --region {region} --output=json --filters Name=attachment.instance-id,Values={instanceId}".format(region=getPresentInstanceRegion(),instanceId=InstanceId)
	data = json.loads(bash(query))
	VolumeIDs = []
	i=0
	while i<len(data['Volumes']):
		vol=[]
		device=data['Volumes'][i]['Attachments'][0]['Device']
		volumeid=data['Volumes'][i]['VolumeId']
		if device == '/dev/sda123':
			i=i+1
			continue
		vol.append(volumeid)
		vol.append(device)
		VolumeIDs.append(vol)
		i=i+1
	if len(VolumeIDs):
		snapshots = createSnapshots(VolumeIDs)
	pass

def getPresentInstanceID():
	"""
	Returns the instance id of the EC2 server on which the script is running.
	"""
	return bash("wget -q -O - http://169.254.169.254/latest/meta-data/instance-id")
def getPresentInstanceRegion():
	"""
	Returns the current EC2 instance underlying AWS region from the AZ.
	"""
	return bash("wget -q -O - http://169.254.169.254/latest/meta-data/placement/availability-zone")[:-1]

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='This script is used to create snapshots of all the EBS Volumes attached to this instance and delete the old snapshots with a default period of 7 days unless specified.')
	#parser.add_argument('-i','--Instance-id', help='EBS volume ID', required=True)
	parser.add_argument('-d','--delete-old', help='Delete old snapshots? True/False', required=False, type=bool,default=True)
	parser.add_argument('-x','--expiry-days', help='Number of days to keep snapshots. Default=7', required=False, type=int, default=7)
	args = parser.parse_args()

logging.basicConfig(filename='backup.log', level=logging.DEBUG, format='%(asctime)s:%(message)s', datefmt='%Y-%m-%d %I:%M:%S%p')
#getInstanceVolumeIds(args.Instance_id)
getInstanceVolumeIds(getPresentInstanceID())
if args.delete_old:
	deleteOldSnapshots(getOurSnapshots(), args.expiry_days)
 

